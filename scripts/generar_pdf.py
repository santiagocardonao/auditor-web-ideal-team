#!/usr/bin/env python3
"""Genera el informe en PDF a partir de informe.json.

Uso: python3 generar_pdf.py informe.json --salida informe.pdf [--logo logo.png]

Arma un HTML con assets/plantilla-informe.html y lo imprime a PDF con Chrome,
Chromium o Edge en modo headless. Si no hay navegador, deja el HTML.
"""

import argparse
import base64
import html
import json
import mimetypes
import os
import shutil
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
PLANTILLA = os.path.join(AQUI, "..", "assets", "plantilla-informe.html")
AREAS = ["SEO técnico", "Rendimiento", "Contenido", "UX", "Orgánico", "Conversión", "Seguridad", "Medición"]
ORDEN_SEV = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
NAVEGADORES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

e = lambda s: html.escape(str(s if s is not None else ""))


def color(p):
    if p is None or p == "N/D":
        return "gris"
    return "verde" if p >= 80 else "amarillo" if p >= 50 else "rojo"


def bloque_hallazgo(h):
    return ('<div class="prioridad"><div class="t"><span class="sev sev-%s">%s</span>%s</div>'
            '<div class="det"><b>Por qué importa:</b> %s</div>'
            '<div class="det"><b>Qué hacer:</b> %s <i>(esfuerzo %s)</i></div>'
            '<div class="det"><b>Evidencia:</b> %s</div></div>') % (
        e(h.get("severidad")), e(h.get("severidad")), e(h.get("titulo")), e(h.get("impacto")),
        e(h.get("recomendacion")), e(h.get("esfuerzo")), e(h.get("evidencia")))


def construir(inf, logo):
    partes = []
    logo_html = ""
    if logo:
        tipo = mimetypes.guess_type(logo)[0] or "image/png"
        with open(logo, "rb") as f:
            logo_html = '<img src="data:%s;base64,%s" alt="">' % (tipo, base64.b64encode(f.read()).decode())
    partes.append('<div class="portada"><div><h1>Auditoría web mensual</h1>'
                  '<div class="meta">%s · %s · Periodo %s · Plataforma: %s</div></div>%s</div>' % (
                      e(inf.get("cliente") or ""), e(inf.get("sitio")), e(inf.get("periodo")),
                      e(inf.get("plataforma")), logo_html))
    partes.append('<div class="resumen">%s</div>' % e(inf.get("resumen_ejecutivo")))

    puntajes = inf.get("puntaje_por_area", {})
    partes.append("<h2>Estado por área</h2><div class=\"tarjetas\">")
    for area in AREAS + [a for a in puntajes if a not in AREAS]:
        if area not in puntajes and area not in AREAS:
            continue
        p = puntajes.get(area, "N/D")
        partes.append('<div class="tarjeta %s"><div class="n">%s</div><div class="a">%s</div></div>' % (
            color(p if isinstance(p, (int, float)) else None), e(p), e(area)))
    partes.append("</div>")

    hallazgos = inf.get("hallazgos", [])
    por_id = {h.get("id"): h for h in hallazgos}
    top = [por_id[i] for i in inf.get("top_prioridades", []) if i in por_id]
    if not top:
        top = sorted(hallazgos, key=lambda h: ORDEN_SEV.get(h.get("severidad"), 9))[:8]
    partes.append("<h2>Prioridades</h2>")
    partes += [bloque_hallazgo(h) for h in top]

    comp = inf.get("comparacion_mes_anterior")
    partes.append("<h2>Comparación con el mes anterior</h2>")
    if comp:
        for titulo, clave, clase in (("Mejoró", "mejoras", "up"), ("Empeoró", "deterioros", "down")):
            filas = comp.get(clave, [])
            if not filas:
                continue
            partes.append("<h3>%s</h3><table><tr><th>Métrica</th><th>Antes</th><th>Ahora</th><th>Cambio</th></tr>" % titulo)
            for f in filas:
                var = "%s%%" % f["variacion_pct"] if f.get("variacion_pct") is not None else ""
                # La flecha indica si el número subió o bajó; el color, si eso es bueno o malo.
                flecha = "↑" if f["ahora"] > f["antes"] else "↓"
                partes.append('<tr><td>%s</td><td>%s</td><td>%s</td><td class="%s">%s %s</td></tr>' % (
                    e(f["metrica"].replace("_", " ")), e(f["antes"]), e(f["ahora"]), clase, flecha, e(var)))
            partes.append("</table>")
    else:
        partes.append("<p>Primera auditoría de este sitio: estos resultados son la línea base para el próximo mes.</p>")

    partes.append("<h2>Hallazgos por área</h2>")
    grupos = {}
    for h in hallazgos:
        grupos.setdefault(h.get("area") or "Otros", []).append(h)
    for area, hs in grupos.items():
        partes.append("<h3>%s</h3><table><tr><th style='width:9%%'>Sev.</th><th style='width:30%%'>Hallazgo</th>"
                      "<th style='width:33%%'>Recomendación</th><th>Evidencia</th></tr>" % e(area))
        for h in sorted(hs, key=lambda h: ORDEN_SEV.get(h.get("severidad"), 9)):
            partes.append('<tr><td><span class="sev sev-%s">%s</span></td><td>%s</td><td>%s</td><td class="ev">%s</td></tr>' % (
                e(h.get("severidad")), e(h.get("severidad")), e(h.get("titulo")), e(h.get("recomendacion")),
                e(h.get("evidencia"))))
        partes.append("</table>")

    if inf.get("proximo_mes"):
        partes.append("<h2>Para el próximo mes</h2><ul>")
        for p in inf["proximo_mes"]:
            partes.append("<li><b>%s</b> (%s): %s</li>" % (e(p.get("titulo")), e(p.get("tipo")), e(p.get("por_que"))))
        partes.append("</ul>")

    if inf.get("no_evaluado"):
        partes.append("<h2>No evaluado este mes</h2><table><tr><th>Chequeo</th><th>Motivo</th></tr>")
        for n in inf["no_evaluado"]:
            partes.append("<tr><td>%s %s</td><td>%s</td></tr>" % (e(n.get("chequeo")), e(n.get("nombre")), e(n.get("motivo"))))
        partes.append("</table>")

    partes.append('<div class="aviso">%s</div>' % e(inf.get("aviso") or "Este informe no sustituye una auditoría de ciberseguridad."))
    with open(PLANTILLA, encoding="utf-8") as f:
        plantilla = f.read()
    return (plantilla.replace("{{sitio}}", e(inf.get("sitio"))).replace("{{periodo}}", e(inf.get("periodo")))
            .replace("{{contenido}}", "\n".join(partes)))


def navegador():
    for n in NAVEGADORES:
        if os.path.isabs(n) and os.path.exists(n):
            return n
        encontrado = shutil.which(n)
        if encontrado:
            return encontrado
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("informe")
    ap.add_argument("--salida", required=True)
    ap.add_argument("--logo")
    a = ap.parse_args()
    with open(a.informe, encoding="utf-8") as f:
        inf = json.load(f)
    ruta_html = os.path.splitext(a.salida)[0] + ".html"
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(construir(inf, a.logo))
    nav = navegador()
    if not nav:
        print("No encontré Chrome/Chromium/Edge. HTML listo en %s: ábrelo e imprime como PDF." % ruta_html)
        return
    cmd = [nav, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf=" + os.path.abspath(a.salida),
           "file://" + os.path.abspath(ruta_html)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not os.path.exists(a.salida):
        sys.exit("Falló la conversión a PDF: %s\nHTML disponible en %s" % (r.stderr[-500:], ruta_html))
    print("PDF: %s\nHTML: %s" % (a.salida, ruta_html))


if __name__ == "__main__":
    main()
