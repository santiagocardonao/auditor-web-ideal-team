#!/usr/bin/env python3
"""Chequeos pasivos de seguridad y confianza (agente 4). No hace pruebas intrusivas.

Uso: python3 seguridad.py https://dominio.com --rastreo rastreo.json --salida seguridad.json
"""

import argparse
import datetime
import json
import re
import socket
import ssl
import urllib.parse

from comun import guardar_json, pedir, seguir

HEADERS_SEG = ["strict-transport-security", "x-content-type-options", "x-frame-options",
               "referrer-policy", "permissions-policy"]

# Palabras típicas de spam inyectado en sitios hackeados. Es una alerta, no una prueba:
# el agente revisa cada coincidencia antes de reportarla.
SOSPECHOSOS = re.compile(
    r"casino|poker|slot-?online|1xbet|bet365|apuestas|viagra|cialis|kamagra|payday|porn|xxx|escort|"
    r"togel|judi|gacor|pills-?online|replica-?watch", re.I)

LEGALES = {
    "privacidad": re.compile(r"privacidad|privacy|tratamiento de datos|habeas data|protecci[oó]n de datos", re.I),
    "terminos": re.compile(r"t[eé]rminos|condiciones|terms|legal", re.I),
    "cookies": re.compile(r"cookies", re.I),
}

# Solo se verifica si responden 200; no se descarga ni se intenta explotar nada.
EXPUESTOS = {
    "comun": ["/.git/HEAD", "/.env", "/backup.zip", "/phpinfo.php"],
    "wordpress": ["/readme.html", "/xmlrpc.php", "/wp-json/wp/v2/users", "/wp-content/uploads/", "/wp-config.php.bak",
                  "/wp-content/debug.log"],
}


def certificado(host):
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, 443), timeout=15) as s:
            with ctx.wrap_socket(s, server_hostname=host) as ss:
                c = ss.getpeercert()
        vence = datetime.datetime.strptime(c["notAfter"], "%b %d %H:%M:%S %Y %Z")
        sans = [v for k, v in c.get("subjectAltName", []) if k == "DNS"]
        emisor = dict(x[0] for x in c.get("issuer", []))
        return {"valido": True, "vence": vence.strftime("%Y-%m-%d"),
                "dias_para_vencer": (vence - datetime.datetime.utcnow()).days,
                "emisor": emisor.get("organizationName"), "dominios": sans}
    except ssl.SSLCertVerificationError as e:
        return {"valido": False, "error": e.verify_message or str(e)}
    except Exception as e:
        return {"valido": None, "error": str(e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--rastreo")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--plataforma", default="")
    a = ap.parse_args()

    p = urllib.parse.urlsplit(a.url)
    host = p.netloc
    host_sin_www = host[4:] if host.startswith("www.") else host
    res = {"sitio": a.url, "aviso": "Revisión pasiva; no sustituye una auditoría de ciberseguridad."}

    # 4.01 Redirecciones http/https y www
    variantes = {}
    for v in ["http://" + host_sin_www, "http://www." + host_sin_www, "https://" + host_sin_www, "https://www." + host_sin_www]:
        r, cadena = seguir(v + "/", leer_cuerpo=False)
        variantes[v] = {"final": cadena[-1]["url"], "status_final": r["status"],
                        "codigos": [c["status"] for c in cadena], "error": r["error"]}
    finales = {x["final"].rstrip("/") for x in variantes.values() if x["status_final"] == 200}
    res["redirecciones"] = {"variantes": variantes, "un_solo_destino": len(finales) <= 1,
                            "todas_a_https": all(x["final"].startswith("https://") for x in variantes.values()
                                                 if x["status_final"] == 200)}

    # 4.02 Certificado
    res["certificado"] = certificado(host)
    # ¿El certificado cubre también la otra variante (con o sin www)?
    otro = "www." + host_sin_www if not host.startswith("www.") else host_sin_www
    dominios = res["certificado"].get("dominios", [])
    res["certificado"]["cubre_variante"] = any(d == otro or (d.startswith("*.") and otro.endswith(d[1:])) for d in dominios) if dominios else None

    # 4.04 Headers
    r, _ = seguir(a.url)
    hdr = r["headers"]
    csp = hdr.get("content-security-policy", "")
    res["headers"] = {h: hdr.get(h) for h in HEADERS_SEG}
    if not res["headers"]["x-frame-options"] and "frame-ancestors" in csp:
        res["headers"]["x-frame-options"] = "(vía CSP frame-ancestors)"
    res["headers"]["content-security-policy"] = csp[:300] or None
    res["headers_presentes"] = sum(1 for h in HEADERS_SEG if res["headers"].get(h))
    res["server"] = hdr.get("server")
    res["x_powered_by"] = hdr.get("x-powered-by")

    # Sobre el rastreo: contenido mixto, enlaces sospechosos, legales, generator
    mixto, sospechosos, legales, generators = [], [], {k: [] for k in LEGALES}, set()
    if a.rastreo:
        with open(a.rastreo, encoding="utf-8") as f:
            rastreo = json.load(f)
        for pag in rastreo["paginas"]:
            if pag.get("recursos_http") and pag["url"].startswith("https://"):
                mixto.append({"url": pag["url"], "recursos": pag["recursos_http"][:10]})
            if pag.get("generator"):
                generators.add(pag["generator"])
            for e in pag.get("enlaces_externos", []):
                dominio = urllib.parse.urlsplit(e["href"]).netloc
                if SOSPECHOSOS.search(dominio) or (e.get("oculto") and e["href"]):
                    sospechosos.append({"pagina": pag["url"], "href": e["href"], "texto": e.get("texto"),
                                        "oculto": e.get("oculto")})
            for interno in pag.get("enlaces_internos", []):
                for k, rx in LEGALES.items():
                    if rx.search(urllib.parse.urlsplit(interno).path) and interno not in legales[k]:
                        legales[k].append(interno)
        dominios_ext = {}
        for u in rastreo.get("externos_desde", {}):
            d = urllib.parse.urlsplit(u).netloc
            dominios_ext[d] = dominios_ext.get(d, 0) + 1
        res["dominios_externos"] = sorted(dominios_ext.items(), key=lambda x: -x[1])[:60]
        # URLs del sitio con pinta de spam inyectado
        res["urls_internas_sospechosas"] = [pg["url"] for pg in rastreo["paginas"]
                                            if SOSPECHOSOS.search(urllib.parse.urlsplit(pg["url"]).path)][:30]
    res["contenido_mixto"] = mixto[:50]
    res["enlaces_sospechosos"] = sospechosos[:50]
    res["paginas_legales"] = {k: v[:5] for k, v in legales.items()}
    res["generator"] = sorted(generators)

    # 4.08 Exposición: solo estado HTTP
    rutas = list(EXPUESTOS["comun"])
    if "wordpress" in a.plataforma.lower():
        rutas += EXPUESTOS["wordpress"]
    base = "%s://%s" % (p.scheme, host)
    expuestos = {}
    for ruta in rutas:
        rr = pedir(base + ruta, leer_cuerpo=ruta.endswith("/") or ruta.endswith("users"), max_bytes=20000)
        info = {"status": rr["status"]}
        if rr["status"] == 200 and ruta.endswith("/"):
            info["listado_directorio"] = "index of" in rr["cuerpo"].lower()
        if rr["status"] == 200 and ruta.endswith("users"):
            try:
                info["usuarios_enumerables"] = len(json.loads(rr["cuerpo"])) > 0
            except ValueError:
                info["usuarios_enumerables"] = False
        expuestos[ruta] = info
    res["rutas_expuestas"] = expuestos

    res["metricas"] = {
        "ssl_dias_para_vencer": res["certificado"].get("dias_para_vencer"),
        "paginas_contenido_mixto": len(mixto),
        "headers_seguridad_presentes": res["headers_presentes"],
        "enlaces_externos_sospechosos": len(sospechosos),
        "avisos_legales_presentes": sum(1 for v in legales.values() if v),
    }
    guardar_json(res, a.salida)
    print(json.dumps(res["metricas"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
