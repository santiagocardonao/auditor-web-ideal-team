#!/usr/bin/env python3
"""Calcula los problemas técnicos a partir de rastreo.json (agente 1).

Uso: python3 analizar_rastreo.py rastreo.json [--salida analisis_tecnico.json]
"""

import argparse
import json
import urllib.parse
from collections import defaultdict

from comun import guardar_json, normalizar


def principal(rastreo):
    paginas = rastreo["paginas"]
    desde = rastreo.get("enlazada_desde", {})
    por_url = {p["url"]: p for p in paginas}
    html = [p for p in paginas if p.get("status") == 200 and "title" in p]

    estado = {p["url"]: p.get("status") for p in paginas}
    estado.update(rastreo.get("estado_enlaces_no_rastreados", {}))

    errores = []
    for url, st in estado.items():
        if st is None or st >= 400:
            errores.append({"url": url, "status": st, "enlazada_desde": desde.get(url, [])[:10],
                            "en_sitemap": url in rastreo.get("urls_sitemap", [])})

    redirecciones, cadenas, temporales = [], [], []
    for p in paginas:
        cad = p.get("cadena", [])
        if len(cad) > 1:
            item = {"url": p["url"], "destino": cad[-1]["url"], "saltos": len(cad) - 1,
                    "codigos": [c["status"] for c in cad[:-1]], "enlazada_desde": desde.get(p["url"], [])[:5]}
            if item["enlazada_desde"]:
                redirecciones.append(item)
            if len(cad) > 2:
                cadenas.append(item)
            if any(c in (302, 307) for c in item["codigos"]):
                temporales.append(item)

    def agrupar(campo):
        g = defaultdict(list)
        for p in html:
            v = (p.get(campo) or "").strip().lower()
            if v:
                g[v].append(p["url"])
        return {k: v for k, v in g.items() if len(v) > 1}

    titles_faltantes = [p["url"] for p in html if not p.get("title")]
    titles_largo = [{"url": p["url"], "largo": len(p["title"])} for p in html
                    if p.get("title") and (len(p["title"]) > 60 or len(p["title"]) < 30)]
    desc_faltantes = [p["url"] for p in html if not p.get("meta_description")]
    desc_largas = [{"url": p["url"], "largo": len(p["meta_description"])} for p in html
                   if p.get("meta_description") and len(p["meta_description"]) > 160]

    sin_h1 = [p["url"] for p in html if not p.get("h1")]
    varios_h1 = [{"url": p["url"], "h1": p["h1"]} for p in html if len(p.get("h1", [])) > 1]
    saltos = []
    for p in html:
        niveles = p.get("niveles_encabezado", [])
        for a, b in zip(niveles, niveles[1:]):
            if b - a > 1:
                saltos.append({"url": p["url"], "de": "H%d" % a, "a": "H%d" % b})
                break

    canon = []
    for p in html:
        c = p.get("canonical")
        if not c:
            canon.append({"url": p["url"], "problema": "sin canonical"})
            continue
        cn = normalizar(c)
        if cn.startswith("http://") and p["url"].startswith("https://"):
            canon.append({"url": p["url"], "canonical": c, "problema": "canonical en http"})
        elif cn != normalizar(p["url_final"]):
            st = estado.get(cn)
            problema = "canonical apunta a otra URL"
            if st and st >= 300:
                problema = "canonical apunta a URL con estado %s" % st
            canon.append({"url": p["url"], "canonical": c, "problema": problema})

    noindex = [p["url"] for p in html if "noindex" in (p.get("meta_robots", "") + p.get("x_robots_tag", "")).lower()]

    # Sitemap: URLs que no son 200 indexables
    sitemap_malas = []
    for u in rastreo.get("urls_sitemap", []):
        p = por_url.get(u)
        if not p:
            continue
        if p.get("status") != 200 or len(p.get("cadena", [])) > 1:
            sitemap_malas.append({"url": u, "status": p.get("status"), "problema": "no responde 200 directo"})
        elif u in noindex:
            sitemap_malas.append({"url": u, "problema": "noindex en sitemap"})

    # hreflang
    hreflang = []
    multidioma = any(p.get("hreflang") for p in html)
    if multidioma:
        mapa = {normalizar(p["url_final"]): p for p in html}
        for p in html:
            for h in p.get("hreflang", []):
                destino = normalizar(h["href"])
                otro = mapa.get(destino)
                if destino == normalizar(p["url_final"]):
                    continue
                if not otro:
                    st = estado.get(destino)
                    if st and st != 200:
                        hreflang.append({"url": p["url"], "hreflang": h["hreflang"], "destino": h["href"],
                                         "problema": "destino con estado %s" % st})
                    continue
                if not any(normalizar(x["href"]) == normalizar(p["url_final"]) for x in otro.get("hreflang", [])):
                    hreflang.append({"url": p["url"], "hreflang": h["hreflang"], "destino": h["href"],
                                     "problema": "no recíproco"})
        sin_xdefault = [p["url"] for p in html if p.get("hreflang")
                        and not any(h["hreflang"].lower() == "x-default" for h in p["hreflang"])]
    else:
        sin_xdefault = []

    duplicados = defaultdict(list)
    for p in html:
        if p.get("hash_texto") and p.get("palabras", 0) > 30:
            duplicados[p["hash_texto"]].append(p["url"])
    duplicados = [v for v in duplicados.values() if len(v) > 1]

    enlazadas = set(desde)
    huerfanas = [u for u in rastreo.get("urls_sitemap", []) if u not in enlazadas and u != normalizar(rastreo["sitio"])]

    externos_rotos = [{"url": u, "status": s, "desde": rastreo.get("externos_desde", {}).get(u, [])[:5]}
                      for u, s in rastreo.get("estado_enlaces_externos", {}).items()
                      if s is not None and s >= 400 and s not in (401, 403, 429, 999)]

    jsonld = {"paginas_con_jsonld": 0, "invalidos": [], "tipos": defaultdict(int)}
    for p in html:
        if p.get("jsonld"):
            jsonld["paginas_con_jsonld"] += 1
        for j in p.get("jsonld", []):
            if not j["valido"]:
                jsonld["invalidos"].append({"url": p["url"], "error": j["error"]})
            for t in j.get("tipos", []):
                jsonld["tipos"][str(t)] += 1
    jsonld["tipos"] = dict(jsonld["tipos"])

    imagenes_sin_dim = sum(1 for p in html for i in p.get("imagenes", []) if not (i.get("width") and i.get("height")))
    ttfb = sorted(p["ttfb_ms"] for p in html if p.get("ttfb_ms"))
    lentas = sorted(({"url": p["url"], "ttfb_ms": p["ttfb_ms"]} for p in html if (p.get("ttfb_ms") or 0) > 800),
                    key=lambda x: -x["ttfb_ms"])[:15]
    pesadas = sorted(({"url": p["url"], "kb": round(p["bytes_html"] / 1024)} for p in html if p.get("bytes_html")),
                     key=lambda x: -x["kb"])[:10]

    # Plantillas: primer segmento de la ruta
    plantillas = defaultdict(list)
    for p in html:
        seg = urllib.parse.urlsplit(p["url"]).path.strip("/").split("/")[0] or "(home)"
        plantillas[seg].append(p["url"])
    muestra_plantillas = {k: v[0] for k, v in sorted(plantillas.items(), key=lambda kv: -len(kv[1]))[:10]}

    metricas = {
        "paginas_rastreadas": len(paginas),
        "paginas_html_200": len(html),
        "errores_4xx": sum(1 for e in errores if e["status"] and 400 <= e["status"] < 500),
        "errores_5xx": sum(1 for e in errores if e["status"] and e["status"] >= 500),
        "sin_respuesta": sum(1 for e in errores if e["status"] is None),
        "redirecciones_internas": len(redirecciones),
        "cadenas_redireccion": len(cadenas),
        "titles_faltantes": len(titles_faltantes),
        "titles_duplicados": sum(len(v) for v in agrupar("title").values()),
        "descriptions_faltantes": len(desc_faltantes),
        "descriptions_duplicadas": sum(len(v) for v in agrupar("meta_description").values()),
        "paginas_sin_h1": len(sin_h1),
        "paginas_huerfanas": len(huerfanas),
        "enlaces_rotos": sum(len(e["enlazada_desde"]) for e in errores),
        "externos_rotos": len(externos_rotos),
        "urls_sitemap": len(rastreo.get("urls_sitemap", [])),
        "ttfb_mediana_ms": ttfb[len(ttfb) // 2] if ttfb else None,
    }

    advertencias = []
    if rastreo.get("parametros", {}).get("limite_alcanzado"):
        advertencias.append("El rastreo llegó al límite de páginas: huérfanas y enlaces rotos pueden estar "
                            "incompletos o inflados. Verifica antes de reportarlos o sube --max-paginas.")
    return {
        "advertencias": advertencias,
        "metricas": metricas,
        "robots": {"status": rastreo.get("robots_status"), "contenido": rastreo.get("robots_txt"),
                   "bloqueadas": rastreo.get("bloqueadas_por_robots", [])[:50]},
        "sitemaps": rastreo.get("sitemaps"),
        "errores": errores,
        "redirecciones_desde_enlaces": redirecciones[:50],
        "cadenas_redireccion": cadenas[:50],
        "redirecciones_temporales": temporales[:50],
        "titles": {"faltantes": titles_faltantes, "duplicados": agrupar("title"), "largo_fuera_de_rango": titles_largo},
        "descriptions": {"faltantes": desc_faltantes, "duplicadas": agrupar("meta_description"), "largas": desc_largas},
        "encabezados": {"sin_h1": sin_h1, "varios_h1": varios_h1, "h1_duplicados": agrupar_h1(html), "saltos": saltos[:30]},
        "canonical": canon[:80],
        "noindex": noindex,
        "sitemap_urls_problema": sitemap_malas[:80],
        "hreflang": {"multidioma": multidioma, "problemas": hreflang[:80], "sin_x_default": sin_xdefault[:30]},
        "contenido_duplicado": duplicados[:30],
        "huerfanas": huerfanas[:80],
        "externos_rotos": externos_rotos[:50],
        "datos_estructurados": jsonld,
        "rendimiento_rastreo": {"ttfb_lentas": lentas, "html_mas_pesado": pesadas,
                                "imagenes_sin_dimensiones": imagenes_sin_dim},
        "plantillas_sugeridas_pagespeed": muestra_plantillas,
    }


def agrupar_h1(html):
    g = defaultdict(list)
    for p in html:
        for h in p.get("h1", []):
            if h:
                g[h.lower()].append(p["url"])
    return {k: v for k, v in g.items() if len(v) > 1}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("rastreo")
    ap.add_argument("--salida")
    a = ap.parse_args()
    with open(a.rastreo, encoding="utf-8") as f:
        res = principal(json.load(f))
    if a.salida:
        guardar_json(res, a.salida)
        print(json.dumps(res["metricas"], ensure_ascii=False, indent=2))
    else:
        print(json.dumps(res, ensure_ascii=False, indent=2))
