#!/usr/bin/env python3
"""Analiza datos de Google Search Console (agente 2).

Modo CSV (exportes de Rendimiento → Exportar → CSV, archivos "Consultas.csv" y "Páginas.csv"):
  python3 gsc.py --consultas actual/Consultas.csv [--consultas-anterior anterior/Consultas.csv] \
                 [--paginas actual/Páginas.csv] [--paginas-anterior anterior/Páginas.csv] --salida gsc_analisis.json

Modo API (cuenta de servicio con acceso de lectura a la propiedad; requiere
`pip install google-api-python-client google-auth`):
  python3 gsc.py --api --propiedad sc-domain:dominio.com --credenciales cuenta.json --salida gsc_analisis.json
"""

import argparse
import csv
import datetime
import json
import sys
from collections import defaultdict

# CTR esperado aproximado por posición (orgánico, promedio de estudios públicos). Sirve
# solo para detectar CTR claramente bajo, no como meta.
CTR_REF = {1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.018}

COLUMNAS = {
    "clave": ["consultas principales", "top queries", "consulta", "query", "páginas principales", "top pages",
              "página", "page", "pages"],
    "clics": ["clics", "clicks"],
    "impresiones": ["impresiones", "impressions"],
    "ctr": ["ctr"],
    "posicion": ["posición", "posicion", "position"],
}


def _num(v):
    v = (v or "").strip().replace("%", "").replace(" ", "")
    if not v:
        return 0.0
    if "," in v and "." not in v:
        v = v.replace(",", ".")
    else:
        v = v.replace(",", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        lector = csv.reader(f)
        cab = [c.strip().lower() for c in next(lector)]
        idx = {}
        for campo, nombres in COLUMNAS.items():
            for i, c in enumerate(cab):
                if c in nombres:
                    idx[campo] = i
                    break
        if "clave" not in idx:
            idx["clave"] = 0
        filas = {}
        for fila in lector:
            if not fila:
                continue
            crudo_ctr = fila[idx["ctr"]] if "ctr" in idx else "0"
            ctr = _num(crudo_ctr)
            if "%" in crudo_ctr:
                ctr /= 100
            filas[fila[idx["clave"]]] = {
                "clics": _num(fila[idx["clics"]]) if "clics" in idx else 0,
                "impresiones": _num(fila[idx["impresiones"]]) if "impresiones" in idx else 0,
                "ctr": ctr,
                "posicion": _num(fila[idx["posicion"]]) if "posicion" in idx else 0,
            }
        return filas


def api(propiedad, credenciales):
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit("Faltan librerías: pip install google-api-python-client google-auth")
    cred = service_account.Credentials.from_service_account_file(
        credenciales, scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    svc = build("searchconsole", "v1", credentials=cred, cache_discovery=False)
    fin = datetime.date.today() - datetime.timedelta(days=3)  # GSC tarda ~2-3 días
    periodos = {
        "actual": (fin - datetime.timedelta(days=27), fin),
        "anterior": (fin - datetime.timedelta(days=55), fin - datetime.timedelta(days=28)),
        "anio_pasado": (fin - datetime.timedelta(days=27 + 364), fin - datetime.timedelta(days=364)),
    }

    def consulta(dims, ini, fin_):
        filas, inicio = [], 0
        while True:
            r = svc.searchanalytics().query(siteUrl=propiedad, body={
                "startDate": ini.isoformat(), "endDate": fin_.isoformat(), "dimensions": dims,
                "rowLimit": 25000, "startRow": inicio}).execute()
            lote = r.get("rows", [])
            filas += lote
            if len(lote) < 25000:
                return filas
            inicio += 25000

    def a_dict(filas):
        return {"|".join(f["keys"]): {"clics": f["clicks"], "impresiones": f["impressions"],
                                      "ctr": f["ctr"], "posicion": f["position"]} for f in filas}

    datos = {"periodos": {k: [v[0].isoformat(), v[1].isoformat()] for k, v in periodos.items()}}
    for nombre, (ini, fin_) in periodos.items():
        datos[nombre] = {"consultas": a_dict(consulta(["query"], ini, fin_)),
                         "paginas": a_dict(consulta(["page"], ini, fin_))}
    datos["consulta_pagina"] = consulta(["query", "page"], *periodos["actual"])
    return datos


def totales(filas):
    c = sum(f["clics"] for f in filas.values())
    i = sum(f["impresiones"] for f in filas.values())
    pos = sum(f["posicion"] * f["impresiones"] for f in filas.values()) / i if i else 0
    return {"clics": round(c), "impresiones": round(i), "ctr": round(c / i, 4) if i else 0, "posicion_media": round(pos, 1)}


def variacion(a, b):
    if not b:
        return None
    return round((a - b) / b * 100, 1)


def comparar(act, ant, n=20):
    filas = []
    for k in set(act) | set(ant):
        x, y = act.get(k, {"clics": 0, "impresiones": 0, "posicion": 0}), ant.get(k, {"clics": 0, "impresiones": 0, "posicion": 0})
        filas.append({"clave": k, "clics": x["clics"], "clics_antes": y["clics"], "delta_clics": x["clics"] - y["clics"],
                      "posicion": round(x["posicion"], 1), "posicion_antes": round(y["posicion"], 1),
                      "impresiones": x["impresiones"], "impresiones_antes": y["impresiones"]})
    pierden = sorted((f for f in filas if f["delta_clics"] < 0), key=lambda f: f["delta_clics"])[:n]
    ganan = sorted((f for f in filas if f["delta_clics"] > 0), key=lambda f: -f["delta_clics"])[:n]
    caen_pos = sorted((f for f in filas if f["posicion_antes"] and f["posicion"] and f["posicion"] - f["posicion_antes"] >= 3
                       and f["impresiones_antes"] >= 50), key=lambda f: f["posicion_antes"] - f["posicion"])[:n]
    return {"pierden_clics": pierden, "ganan_clics": ganan, "caen_posicion": caen_pos}


def analizar(consultas, consultas_ant=None, paginas=None, paginas_ant=None, consulta_pagina=None, anio_pasado=None):
    res = {}
    t = totales(consultas)
    res["totales"] = t
    if consultas_ant:
        ta = totales(consultas_ant)
        res["totales_anterior"] = ta
        res["variacion_pct"] = {k: variacion(t[k], ta[k]) for k in ("clics", "impresiones", "ctr")}
        res["variacion_pct"]["posicion_media"] = round(t["posicion_media"] - ta["posicion_media"], 1)
        res["consultas_cambios"] = comparar(consultas, consultas_ant)
    if anio_pasado:
        res["totales_anio_pasado"] = totales(anio_pasado)
    orden = sorted(consultas.items(), key=lambda kv: -kv[1]["clics"])
    res["top_consultas_clics"] = [dict(clave=k, **v) for k, v in orden[:20]]
    res["top_consultas_impresiones"] = [dict(clave=k, **v) for k, v in sorted(consultas.items(), key=lambda kv: -kv[1]["impresiones"])[:20]]
    bajo_ctr = []
    for k, v in consultas.items():
        pos = round(v["posicion"])
        if 1 <= pos <= 10 and v["impresiones"] >= 100 and v["ctr"] < CTR_REF[pos] * 0.5:
            bajo_ctr.append(dict(clave=k, ctr_referencia=CTR_REF[pos], **v))
    res["ctr_bajo"] = sorted(bajo_ctr, key=lambda x: -x["impresiones"])[:25]
    res["oportunidades_pos_8_30"] = sorted(
        (dict(clave=k, **v) for k, v in consultas.items() if 8 <= v["posicion"] <= 30 and v["impresiones"] >= 50),
        key=lambda x: -x["impresiones"])[:25]
    if paginas:
        res["totales_paginas"] = totales(paginas)
        res["top_paginas"] = [dict(clave=k, **v) for k, v in sorted(paginas.items(), key=lambda kv: -kv[1]["clics"])[:20]]
        res["paginas_menos_visibles"] = [dict(clave=k, **v) for k, v in sorted(paginas.items(), key=lambda kv: kv[1]["impresiones"])[:20]]
        if paginas_ant:
            res["paginas_cambios"] = comparar(paginas, paginas_ant)
    if consulta_pagina:
        por_consulta = defaultdict(list)
        for f in consulta_pagina:
            q, pag = f["keys"]
            por_consulta[q].append({"pagina": pag, "clics": f["clicks"], "impresiones": f["impressions"], "posicion": round(f["position"], 1)})
        canib = []
        for q, pags in por_consulta.items():
            relevantes = [p for p in pags if p["impresiones"] >= 20]
            total = sum(p["impresiones"] for p in relevantes)
            if len(relevantes) >= 2 and total >= 100 and min(p["impresiones"] for p in relevantes) / total >= 0.15:
                canib.append({"consulta": q, "paginas": sorted(relevantes, key=lambda p: -p["impresiones"])})
        res["canibalizacion"] = sorted(canib, key=lambda c: -sum(p["impresiones"] for p in c["paginas"]))[:25]
    else:
        res["canibalizacion"] = None
        res["nota_canibalizacion"] = "Requiere datos consulta×página (modo API). No evaluado con CSV."
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--consultas")
    ap.add_argument("--consultas-anterior")
    ap.add_argument("--paginas")
    ap.add_argument("--paginas-anterior")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--propiedad")
    ap.add_argument("--credenciales")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    if a.api:
        if not (a.propiedad and a.credenciales):
            sys.exit("--api necesita --propiedad y --credenciales")
        d = api(a.propiedad, a.credenciales)
        res = analizar(d["actual"]["consultas"], d["anterior"]["consultas"], d["actual"]["paginas"],
                       d["anterior"]["paginas"], d["consulta_pagina"], d["anio_pasado"]["consultas"])
        res["periodos"] = d["periodos"]
        res["fuente"] = "api"
    else:
        if not a.consultas:
            sys.exit("Indica --consultas (CSV) o usa --api")
        leer = lambda r: leer_csv(r) if r else None
        res = analizar(leer(a.consultas), leer(a.consultas_anterior), leer(a.paginas), leer(a.paginas_anterior))
        res["fuente"] = "csv"
    with open(a.salida, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps({"totales": res["totales"], "variacion_pct": res.get("variacion_pct")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
