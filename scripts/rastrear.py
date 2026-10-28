#!/usr/bin/env python3
"""Rastrea un sitio (solo lectura) y guarda todo lo que necesitan los agentes.

Uso:
  python3 rastrear.py https://dominio.com --salida rastreo.json [--max-paginas 300] [--pausa 0.5]

Respeta robots.txt, no sale del dominio, sigue enlaces internos y además
visita las URLs del sitemap. Verifica el estado de enlaces internos no
rastreados y de una muestra de enlaces externos.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import deque

from comun import ParserPagina, USER_AGENT, guardar_json, mismo_sitio, normalizar, pedir, seguir

EXT_NO_HTML = re.compile(r"\.(jpe?g|png|gif|webp|avif|svg|ico|pdf|zip|rar|mp4|mp3|webm|mov|docx?|xlsx?|pptx?|css|js|woff2?|ttf|eot|xml|txt)$", re.I)

MEDICION = {
    "ga4": re.compile(r"\bG-[A-Z0-9]{6,12}\b"),
    "gtm": re.compile(r"\bGTM-[A-Z0-9]{4,9}\b"),
    "universal_analytics": re.compile(r"\bUA-\d{4,10}-\d{1,4}\b"),
    "google_ads": re.compile(r"\bAW-\d{6,12}\b"),
    "meta_pixel": re.compile(r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d{10,20})"),
}
MEDICION_SCRIPTS = {
    "tiktok_pixel": "analytics.tiktok.com",
    "hotjar": "static.hotjar.com",
    "clarity": "clarity.ms",
    "linkedin": "snap.licdn.com",
}


def leer_sitemaps(base, robots_txt):
    sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_txt or "")
    if not sitemaps:
        sitemaps = [urllib.parse.urljoin(base, "/sitemap.xml"), urllib.parse.urljoin(base, "/sitemap_index.xml")]
    vistos, urls, info = set(), [], []
    cola = list(sitemaps)
    while cola and len(vistos) < 50:
        sm = cola.pop(0)
        if sm in vistos:
            continue
        vistos.add(sm)
        r, cadena = seguir(sm)
        entrada = {"url": sm, "status": r["status"], "urls": 0, "error": None}
        if r["status"] == 200 and r["cuerpo"].strip():
            try:
                raiz = ET.fromstring(r["cuerpo"].encode("utf-8"))
                ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
                for s in raiz.iter(ns + "sitemap"):
                    loc = s.find(ns + "loc")
                    if loc is not None and loc.text:
                        cola.append(loc.text.strip())
                for u in raiz.iter(ns + "url"):
                    loc = u.find(ns + "loc")
                    if loc is not None and loc.text:
                        urls.append(normalizar(loc.text.strip()))
                        entrada["urls"] += 1
            except ET.ParseError as e:
                entrada["error"] = "XML inválido: %s" % e
        info.append(entrada)
    existentes = [i for i in info if i["status"] == 200]
    return (existentes or info[:1]), sorted(set(urls))


def analizar_pagina(url, r, cadena, host):
    p = ParserPagina(cadena[-1]["url"])
    try:
        p.feed(r["cuerpo"])
    except Exception:
        pass
    texto = p.texto_visible()
    internos, externos = [], []
    for e in p.enlaces:
        href = e["href"]
        if href.startswith(("mailto:", "tel:", "javascript:", "whatsapp:")) or e["href_crudo"].startswith("#"):
            continue
        if not href.startswith("http"):
            continue
        (internos if mismo_sitio(href, host) else externos).append(e)
    html_todo = r["cuerpo"] + " ".join(p.scripts_inline)
    medicion = {}
    for clave, rx in MEDICION.items():
        ids = sorted(set(rx.findall(html_todo)))
        if ids:
            medicion[clave] = ids
    for clave, dominio in MEDICION_SCRIPTS.items():
        if dominio in html_todo:
            medicion[clave] = True
    jsonld = []
    for bloque in p.jsonld:
        try:
            datos = json.loads(bloque)
            tipos = []
            for d in (datos if isinstance(datos, list) else [datos]):
                if isinstance(d, dict):
                    if "@graph" in d:
                        tipos += [g.get("@type") for g in d["@graph"] if isinstance(g, dict)]
                    else:
                        tipos.append(d.get("@type"))
            jsonld.append({"valido": True, "tipos": tipos})
        except ValueError as ex:
            jsonld.append({"valido": False, "error": str(ex)[:200]})
    contactos = sorted(set(e["href_crudo"] for e in p.enlaces
                           if e["href_crudo"].startswith(("tel:", "mailto:")) or "wa.me" in e["href"]
                           or "api.whatsapp.com" in e["href"]))
    return {
        "url": url,
        "url_final": cadena[-1]["url"],
        "status": r["status"],
        "cadena": cadena,
        "ttfb_ms": r["ttfb_ms"],
        "bytes_html": r["bytes"],
        "content_type": r["headers"].get("content-type", ""),
        "x_robots_tag": r["headers"].get("x-robots-tag", ""),
        "title": (p.title or "").strip() or None,
        "meta_description": p.metas.get("description"),
        "meta_robots": p.metas.get("robots", ""),
        "generator": p.metas.get("generator"),
        "og_title": p.metas.get("og:title"),
        "idioma": p.lang,
        "canonical": p.canonical,
        "hreflang": p.hreflang,
        "h1": [t for n, t in p.encabezados if n == 1],
        "h2": [t for n, t in p.encabezados if n == 2][:30],
        "niveles_encabezado": [n for n, _ in p.encabezados],
        "palabras": len(texto.split()),
        "hash_texto": hashlib.md5(texto.lower().encode("utf-8")).hexdigest() if texto else None,
        "texto": texto[:6000],
        "enlaces_internos": sorted(set(normalizar(e["href"]) for e in internos)),
        "enlaces_externos": [{"href": e["href"], "texto": e["texto"], "rel": e["rel"], "oculto": e["oculto"]}
                             for e in externos][:200],
        "contactos": contactos,
        "imagenes": p.imagenes[:150],
        "scripts": p.scripts,
        "estilos": p.estilos,
        "iframes": p.iframes,
        "jsonld": jsonld,
        "formularios": p.formularios,
        "medicion": medicion,
        "recursos_http": sorted(set(u for u in [i["src"] for i in p.imagenes] + [s["src"] for s in p.scripts]
                                    + p.estilos + p.iframes if u.startswith("http://"))),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--max-paginas", type=int, default=300)
    ap.add_argument("--pausa", type=float, default=0.5)
    ap.add_argument("--max-externos", type=int, default=150, help="enlaces externos a verificar (HEAD)")
    a = ap.parse_args()

    inicio_r, cadena_inicio = seguir(a.url)
    base = cadena_inicio[-1]["url"]
    host = urllib.parse.urlsplit(base).netloc

    robots = pedir(urllib.parse.urljoin(base, "/robots.txt"))
    robots_txt = robots["cuerpo"] if robots["status"] == 200 else None
    rp = urllib.robotparser.RobotFileParser()
    rp.parse((robots_txt or "").splitlines())

    sitemaps, urls_sitemap = leer_sitemaps(base, robots_txt)

    # Primero lo que se descubre navegando desde la home (cubre las plantillas del menú);
    # después lo que solo está en el sitemap.
    cola = deque([normalizar(base)])
    cola_sitemap = deque(u for u in urls_sitemap if mismo_sitio(u, host) and u != normalizar(base))
    encolados = set(cola)  # ya en la cola de navegación
    visitadas = set()
    paginas, bloqueadas, enlazada_desde = [], [], {}

    while (cola or cola_sitemap) and len(paginas) < a.max_paginas:
        url = cola.popleft() if cola else cola_sitemap.popleft()
        if url in visitadas:
            continue
        visitadas.add(url)
        if robots_txt and not rp.can_fetch(USER_AGENT, url) and not rp.can_fetch("*", url):
            bloqueadas.append(url)
            continue
        r, cadena = seguir(url)
        es_html = "html" in r["headers"].get("content-type", "")
        if es_html and r["status"] == 200:
            pag = analizar_pagina(url, r, cadena, host)
            for destino in pag["enlaces_internos"]:
                enlazada_desde.setdefault(destino, set()).add(url)
                if destino not in encolados and not EXT_NO_HTML.search(urllib.parse.urlsplit(destino).path):
                    encolados.add(destino)
                    cola.append(destino)
        else:
            pag = {"url": url, "url_final": cadena[-1]["url"], "status": r["status"], "cadena": cadena,
                   "ttfb_ms": r["ttfb_ms"], "content_type": r["headers"].get("content-type", ""),
                   "error": r["error"]}
        paginas.append(pag)
        sys.stderr.write("\r%d páginas, %d en cola" % (len(paginas), len(cola) + len(cola_sitemap)))
        time.sleep(a.pausa)
    sys.stderr.write("\n")

    rastreadas = {p["url"] for p in paginas}
    # Enlaces internos que no alcanzamos a rastrear: verificar estado con HEAD.
    pendientes = [u for u in enlazada_desde if u not in rastreadas][:300]
    estado_extra = {}
    for u in pendientes:
        r = pedir(u, metodo="HEAD", leer_cuerpo=False)
        if r["status"] in (405, 403, None):
            r = pedir(u, leer_cuerpo=False)
        estado_extra[u] = r["status"]
        time.sleep(a.pausa / 2)

    externos = {}
    for p in paginas:
        for e in p.get("enlaces_externos", []):
            externos.setdefault(e["href"].split("#")[0], set()).add(p["url"])
    estado_externos = {}
    for u in list(externos)[: a.max_externos]:
        r = pedir(u, metodo="HEAD", leer_cuerpo=False)
        if r["status"] in (405, 403, None):
            r = pedir(u, leer_cuerpo=False)
        estado_externos[u] = r["status"]

    resultado = {
        "sitio": base,
        "host": host,
        "fecha": time.strftime("%Y-%m-%d"),
        "parametros": {"max_paginas": a.max_paginas, "limite_alcanzado": len(paginas) >= a.max_paginas},
        "robots_txt": robots_txt,
        "robots_status": robots["status"],
        "sitemaps": sitemaps,
        "urls_sitemap": urls_sitemap,
        "bloqueadas_por_robots": bloqueadas,
        "paginas": paginas,
        "enlazada_desde": {k: sorted(v) for k, v in enlazada_desde.items()},
        "estado_enlaces_no_rastreados": estado_extra,
        "estado_enlaces_externos": estado_externos,
        "externos_desde": {k: sorted(v) for k, v in externos.items()},
    }
    guardar_json(resultado, a.salida)
    print(json.dumps({"salida": a.salida, "paginas": len(paginas), "urls_sitemap": len(urls_sitemap),
                      "bloqueadas_por_robots": len(bloqueadas)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
