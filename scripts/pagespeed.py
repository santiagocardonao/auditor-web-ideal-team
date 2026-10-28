#!/usr/bin/env python3
"""Mide URLs con la API de PageSpeed Insights, en móvil y escritorio.

Uso:
  python3 pagespeed.py --urls https://a.com https://a.com/servicios --salida pagespeed.json

Usa la variable de entorno PSI_API_KEY si existe (sin ella la cuota es muy baja).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
AUDITS = ["largest-contentful-paint", "cumulative-layout-shift", "total-blocking-time", "speed-index",
          "first-contentful-paint", "interactive", "server-response-time"]
OPORTUNIDADES = ["render-blocking-resources", "unused-javascript", "unused-css-rules", "uses-optimized-images",
                 "modern-image-formats", "uses-responsive-images", "offscreen-images", "unsized-images",
                 "third-party-summary", "total-byte-weight", "bootup-time", "mainthread-work-breakdown",
                 "font-display", "uses-text-compression", "uses-long-cache-ttl", "dom-size"]


def consultar(url, estrategia, clave):
    q = [("url", url), ("strategy", estrategia), ("category", "performance")]
    if clave:
        q.append(("key", clave))
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q))
    for intento in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r), None
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "replace")[:300]
            if e.code == 429 and "per day" in cuerpo:
                return None, "Cuota diaria agotada: configura PSI_API_KEY (gratis en Google Cloud)."
            if e.code == 429 and intento < 2:
                time.sleep(20)
                continue
            return None, "HTTP %s: %s" % (e.code, cuerpo)
        except Exception as e:
            if intento < 2:
                time.sleep(5)
                continue
            return None, str(e)
    return None, "sin respuesta"


def campo(exp):
    if not exp or "metrics" not in exp:
        return None
    m = exp["metrics"]
    def p75(k):
        return m.get(k, {}).get("percentile")
    cls = p75("CUMULATIVE_LAYOUT_SHIFT_SCORE")
    return {
        "origen": exp.get("id"),
        "categoria": exp.get("overall_category"),
        "lcp_ms": p75("LARGEST_CONTENTFUL_PAINT_MS"),
        "inp_ms": p75("INTERACTION_TO_NEXT_PAINT"),
        "cls": cls / 100 if cls is not None else None,
        "ttfb_ms": p75("EXPERIMENTAL_TIME_TO_FIRST_BYTE"),
        "fcp_ms": p75("FIRST_CONTENTFUL_PAINT_MS"),
    }


def resumir(datos):
    lh = datos.get("lighthouseResult", {})
    audits = lh.get("audits", {})
    lab = {k: audits.get(k, {}).get("numericValue") for k in AUDITS}
    opps = []
    for k in OPORTUNIDADES:
        a = audits.get(k)
        if not a or a.get("score") in (None, 1):
            continue
        items = (a.get("details") or {}).get("items") or []
        opps.append({
            "id": k, "titulo": a.get("title"), "valor": a.get("displayValue"),
            "ahorro_ms": (a.get("details") or {}).get("overallSavingsMs"),
            "top": [{kk: it.get(kk) for kk in ("url", "entity", "totalBytes", "wastedBytes", "wastedMs", "blockingTime")
                     if kk in it} for it in items[:5]],
        })
    return {
        "score": round(lh.get("categories", {}).get("performance", {}).get("score", 0) * 100),
        "lab": lab,
        "campo_url": campo(datos.get("loadingExperience")),
        "campo_origen": campo(datos.get("originLoadingExperience")),
        "oportunidades": opps,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--urls", nargs="+", required=True)
    ap.add_argument("--salida", required=True)
    ap.add_argument("--estrategias", nargs="+", default=["mobile", "desktop"])
    a = ap.parse_args()
    clave = os.environ.get("PSI_API_KEY")
    resultados = []
    for url in a.urls:
        for est in a.estrategias:
            sys.stderr.write("PSI %s (%s)\n" % (url, est))
            datos, error = consultar(url, est, clave)
            fila = {"url": url, "estrategia": est, "error": error}
            if datos:
                fila.update(resumir(datos))
            resultados.append(fila)
            if not clave:
                time.sleep(3)
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump({"con_api_key": bool(clave), "resultados": resultados}, f, ensure_ascii=False, indent=2)
    resumen = [{"url": r["url"], "est": r["estrategia"], "score": r.get("score"), "error": r["error"]} for r in resultados]
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
