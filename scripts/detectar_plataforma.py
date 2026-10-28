#!/usr/bin/env python3
"""Detecta la plataforma con la que está construido un sitio.

Uso: python3 detectar_plataforma.py https://dominio.com
Imprime JSON con plataforma probable, confianza y señales encontradas.
"""

import json
import sys

from comun import seguir

FIRMAS = {
    "wordpress": ["wp-content/", "wp-includes/", "wp-json", 'name="generator" content="wordpress'],
    "framer": ["framerusercontent.com", "framer.com/", "data-framer", "__framer"],
    "shopify": ["cdn.shopify.com", "shopify.theme", "myshopify.com", "shopify-section"],
    "astro": ["astro-island", "data-astro-cid", "/_astro/", 'content="astro'],
    "webflow": ["webflow.js", "data-wf-page", "assets.website-files.com", "cdn.prod.website-files.com"],
    "wix": ["wixstatic.com", "x-wix-", "wix.com website builder"],
    "squarespace": ["squarespace.com", "static1.squarespace.com"],
    "nextjs": ["/_next/static", "__next_data__"],
}

HEADERS = {
    "shopify": ["x-shopid", "x-shopify-stage"],
    "framer": ["x-framer"],
    "wix": ["x-wix-request-id"],
    "wordpress": ["x-pingback"],
}


def detectar(url):
    r, cadena = seguir(url)
    html = r["cuerpo"].lower()
    puntos, senales = {}, {}
    for plat, firmas in FIRMAS.items():
        for f in firmas:
            if f in html:
                puntos[plat] = puntos.get(plat, 0) + 1
                senales.setdefault(plat, []).append(f)
    for plat, hs in HEADERS.items():
        for h in hs:
            if any(k.startswith(h) for k in r["headers"]):
                puntos[plat] = puntos.get(plat, 0) + 2
                senales.setdefault(plat, []).append("header " + h)
    powered = r["headers"].get("x-powered-by", "")
    servidor = r["headers"].get("server", "")
    if r["status"] != 200:
        plataforma, confianza = (max(puntos, key=puntos.get) if puntos else "desconocida"), "no_concluyente"
    elif not puntos:
        plataforma, confianza = "codigo_propio_u_otro", "baja"
    else:
        plataforma = max(puntos, key=puntos.get)
        confianza = "alta" if puntos[plataforma] >= 2 else "media"
    return {
        "url_final": cadena[-1]["url"],
        "status": r["status"],
        "plataforma": plataforma,
        "confianza": confianza,
        "senales": senales,
        "server": servidor,
        "x_powered_by": powered,
        "error": r["error"],
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(detectar(sys.argv[1]), ensure_ascii=False, indent=2))
