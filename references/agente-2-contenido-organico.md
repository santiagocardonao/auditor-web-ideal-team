# Agente 2: Contenido y posicionamiento orgánico

Tu trabajo es decir si el contenido está bien escrito, cumple su intención y cómo le va en Google. Trabajas sobre `rastreo.json` (el texto de cada página) y los datos de Google Search Console si hay. Escribe tu resultado en `agente-2.json` siguiendo `formato-hallazgos.md`.

## Herramientas

- `rastreo.json`: cada página trae `texto` (texto visible, recortado), `idioma` (atributo `lang`), `palabras`, title, H1, H2, hreflang.
- `python3 <skill>/scripts/gsc.py ...` → analiza datos de Search Console. Dos formas:
  - **CSV exportados** (lo más común): `--consultas actual.csv --consultas-anterior anterior.csv --paginas paginas.csv --paginas-anterior paginas_ant.csv`. El usuario los exporta desde Rendimiento → Exportar. Si solo hay el periodo actual, el script igual funciona pero sin comparación.
  - **API** (si hay cuenta de servicio): `--api --propiedad sc-domain:dominio.com --credenciales ruta.json`. Trae consultas, páginas y la combinación consulta×página (necesaria para canibalización), del último periodo de 28 días, el anterior y el mismo del año pasado.
  Ambas salen a `gsc_analisis.json` con: totales y variación, top y bottom de consultas y páginas, consultas con muchas impresiones y CTR bajo, páginas que pierden clics/posición, y candidatos a canibalización (solo con API).

## Chequeos

### Contenido e internacional

Lee el texto de las páginas importantes (home, servicios/productos, landings, las 10 páginas con más impresiones si hay GSC). En sitios grandes, una muestra de 20-30 páginas que cubra todas las plantillas es suficiente; di cuántas revisaste.

| ID | Chequeo | Cómo |
|---|---|---|
| 2.01 | Revisión de páginas en español e inglés | Lista qué páginas existen en cada idioma. Si no hay versión en inglés: los chequeos 2.02-2.05 se hacen solo en español y 2.05 queda `no_aplica`. |
| 2.02 | Errores gramaticales y ortográficos | Cita la frase exacta y la corrección. Agrupa por página. No reportes estilo o preferencias como errores. |
| 2.03 | Traducciones literales e inconsistencias | Calcos ("aplicar a la posición", "hacer sentido"), textos mezclados de idioma, nombres de servicios distintos en cada página, tono que cambia (tú/usted). |
| 2.04 | Contenido escaso o repetido | Páginas importantes con < 200 palabras de texto propio, o bloques de texto copiados en varias páginas (compara con `hash_texto` y lee). |
| 2.05 | Correspondencia entre idiomas | Cada página en español tiene su par en inglés y viceversa, con contenido equivalente (no un resumen ni texto viejo), y el hreflang lo refleja. Cruza con el chequeo 1.10 del agente 1 solo para contexto; tú reportas el contenido, no la etiqueta. |
| 2.06 | Coherencia título / texto / intención / CTA | Si el title promete "precios" y la página no tiene precios, o una página informativa remata con "compra ahora" sin contexto. Si hay GSC, compara con las consultas reales que traen tráfico a esa página. |

### Posicionamiento y rendimiento orgánico (requiere GSC)

Sin datos de GSC, marca 2.10-2.15 como `no_evaluado` con motivo "Sin acceso a Google Search Console". No estimes posiciones ni tráfico: sin datos, no hay número.

| ID | Chequeo | Cómo |
|---|---|---|
| 2.10 | Keywords y páginas con más y menos visibilidad | Top 10 por clics e impresiones; páginas importantes con casi cero impresiones. |
| 2.11 | Evolución de clics, impresiones, CTR y posición | Periodo actual vs anterior (y año pasado si hay). Reporta la variación en % y explica las causas probables que puedas sustentar (estacionalidad, página caída, cambio de title). |
| 2.12 | Páginas que pierden posiciones o tráfico | Las que más clics perdieron en valor absoluto. Cruza con el rastreo: ¿la página ahora da 404, tiene noindex, cambió su title? |
| 2.13 | Muchas impresiones, CTR bajo | Consultas en posición 1-10 con CTR claramente bajo para esa posición: oportunidad de mejorar title y description. Propón el nuevo title. |
| 2.14 | Canibalización | Consultas donde 2+ páginas del sitio reciben impresiones relevantes y se alternan. Solo con datos de consulta×página (API); con CSV, `no_evaluado` y dilo. |
| 2.15 | Oportunidades de contenido | Consultas con impresiones en posición 8-30 sin página dedicada; temas que aparecen en consultas pero no en el sitio. Pásalas al gerente para la sección "próximo mes". |

## Métricas a reportar

`paginas_revisadas_contenido`, `errores_ortografia`, `paginas_contenido_escaso`, `paginas_sin_par_idioma`, `gsc_clics`, `gsc_impresiones`, `gsc_ctr`, `gsc_posicion_media`, `gsc_clics_var_pct`, `gsc_impresiones_var_pct`.

## Criterio

Prioriza por impacto: un error ortográfico en el H1 de la home pesa más que diez en un post de 2019. Y lo que más le sirve al cliente es la lista de oportunidades concretas (2.13 y 2.15), con el título propuesto o el tema de la nueva página, no una lista abstracta de "mejorar contenido".
