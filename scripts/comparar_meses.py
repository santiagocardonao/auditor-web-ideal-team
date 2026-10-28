#!/usr/bin/env python3
"""Junta las métricas de los agentes en resumen.json y compara con el mes anterior.

Uso: python3 comparar_meses.py auditorias/dominio/2026-10 [auditorias/dominio/2026-09]

Si no se da el mes anterior, busca la carpeta hermana más reciente con resumen.json.
"""

import glob
import json
import os
import sys

# Para estas métricas, subir es bueno. Para el resto, subir es malo.
SUBIR_ES_BUENO = {"psi_movil_home", "psi_escritorio_home", "gsc_clics", "gsc_impresiones", "gsc_ctr",
                  "ssl_dias_para_vencer", "headers_seguridad_presentes", "avisos_legales_presentes",
                  "recorridos_criticos_ok", "formularios_ok", "eventos_clave_ok"}
NEUTRAS = {"paginas_rastreadas", "paginas_html_200", "urls_sitemap", "paginas_revisadas_contenido",
           "ssl_dias_para_vencer", "recorridos_criticos_total", "formularios_total", "eventos_clave_total"}
# gsc_posicion_media: bajar es bueno (posición 3 es mejor que 8); queda en el grupo "subir es malo".


def resumen(carpeta):
    metricas, hallazgos = {}, {"critica": 0, "alta": 0, "media": 0, "baja": 0}
    no_evaluados = 0
    for ruta in sorted(glob.glob(os.path.join(carpeta, "agente-*.json"))):
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        for k, v in (d.get("metricas") or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                metricas[k] = v
        for h in d.get("hallazgos", []):
            if h.get("severidad") in hallazgos:
                hallazgos[h["severidad"]] += 1
        no_evaluados += sum(1 for c in d.get("chequeos", []) if c.get("estado") == "no_evaluado")
    return {"periodo": os.path.basename(os.path.normpath(carpeta)), "metricas": metricas,
            "hallazgos_por_severidad": hallazgos, "chequeos_no_evaluados": no_evaluados}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    actual = sys.argv[1]
    res = resumen(actual)
    with open(os.path.join(actual, "resumen.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)

    anterior = sys.argv[2] if len(sys.argv) > 2 else None
    if not anterior:
        padre = os.path.dirname(os.path.normpath(actual))
        hermanas = sorted(d for d in glob.glob(os.path.join(padre, "*"))
                          if os.path.isdir(d) and os.path.basename(d) < os.path.basename(os.path.normpath(actual))
                          and os.path.exists(os.path.join(d, "resumen.json")))
        anterior = hermanas[-1] if hermanas else None
    if not anterior:
        print(json.dumps({"resumen": "resumen.json", "comparacion": None, "nota": "Primera auditoría: línea base"},
                         ensure_ascii=False))
        return

    with open(os.path.join(anterior, "resumen.json"), encoding="utf-8") as f:
        prev = json.load(f)
    mejoras, deterioros, sin_cambio = [], [], []
    for k, v in res["metricas"].items():
        if k not in prev["metricas"]:
            continue
        a = prev["metricas"][k]
        if v == a:
            sin_cambio.append(k)
            continue
        fila = {"metrica": k, "antes": a, "ahora": v, "variacion_pct": round((v - a) / a * 100, 1) if a else None}
        if k in NEUTRAS:
            sin_cambio.append(k)
            continue
        bueno = (v > a) if k in SUBIR_ES_BUENO else (v < a)
        (mejoras if bueno else deterioros).append(fila)
    comp = {"periodo_anterior": prev["periodo"], "periodo_actual": res["periodo"], "mejoras": mejoras,
            "deterioros": deterioros, "sin_cambio": sin_cambio,
            "hallazgos_antes": prev["hallazgos_por_severidad"], "hallazgos_ahora": res["hallazgos_por_severidad"]}
    with open(os.path.join(actual, "comparacion.json"), "w", encoding="utf-8") as f:
        json.dump(comp, f, ensure_ascii=False, indent=2)
    print(json.dumps({"mejoras": len(mejoras), "deterioros": len(deterioros), "anterior": prev["periodo"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
