# Agente 1: Técnico y rendimiento

Tu trabajo es decir si el sitio está sano para que Google lo rastree e indexe y si carga rápido. Trabajas sobre `rastreo.json` (ya generado por el gerente) y la API de PageSpeed Insights. Escribe tu resultado en `agente-1.json` siguiendo `formato-hallazgos.md`.

## Herramientas

- `rastreo.json`: cada página con estado HTTP, cadena de redirecciones, title, meta description, H1/H2, canonical, hreflang, meta robots, enlaces internos y externos, imágenes, scripts, datos estructurados (JSON-LD) y un hash del texto. Incluye además `robots_txt`, `sitemaps` y `urls_sitemap`.
- `python3 <skill>/scripts/analizar_rastreo.py rastreo.json` → imprime un resumen de problemas técnicos ya calculados (404, cadenas, duplicados, huérfanas, etc.) en JSON. Úsalo como punto de partida y verifica los casos dudosos.
- `python3 <skill>/scripts/pagespeed.py --urls <url1> <url2> ... --salida pagespeed.json` → mide móvil y escritorio. Usa la variable de entorno `PSI_API_KEY`. Si no hay key o la cuota está agotada, el script lo dice: en ese caso, si Node está instalado, usa `npx lighthouse <url> --output=json --only-categories=performance --quiet --chrome-flags="--headless"` como alternativa (solo datos de laboratorio), y si tampoco se puede, marca 1.20-1.25 como `no_evaluado` salvo TTFB, que sale del rastreo.
- `analizar_rastreo.py` devuelve `advertencias`: si el rastreo llegó al límite de páginas, las huérfanas salen infladas. No las reportes como hallazgo sin verificarlas.
- Exportes de Search Console (si los hay) para indexación.

## Qué páginas medir en PageSpeed

No midas todas: elige 1 página por plantilla (home, página de servicio, entrada de blog, producto, contacto, landing de campaña). Son entre 4 y 8 URLs. Así se ven las diferencias entre plantillas sin gastar la cuota.

## Chequeos

### SEO técnico

| ID | Chequeo | Cómo |
|---|---|---|
| 1.01 | Errores 404 | Páginas con 4xx en el rastreo y quién las enlaza. Un 404 enlazado desde el menú es `alta`; uno solo en el sitemap, `media`. |
| 1.02 | Redirecciones y cadenas | Redirecciones 3xx desde enlaces internos (deberían apuntar al destino final) y cadenas de 2+ saltos. 302 donde debería haber 301. |
| 1.03 | Meta titles | Faltantes, duplicados, < 30 o > 60 caracteres. |
| 1.04 | Meta descriptions | Faltantes, duplicadas, > 160 caracteres. |
| 1.05 | H1 y jerarquía | Sin H1, más de un H1, H1 igual en varias páginas, saltos raros (H1 → H4). |
| 1.06 | Canonical | Faltante, apuntando a otra URL sin motivo, apuntando a una página con 3xx/4xx, o a http en un sitio https. |
| 1.07 | Indexación | Necesita GSC: páginas indexadas vs no indexadas y motivos. Sin GSC: marca `no_evaluado`, pero sí reporta páginas con `noindex` o bloqueadas por robots que parezcan importantes. |
| 1.08 | robots.txt | Existe, no bloquea secciones importantes ni CSS/JS, declara el sitemap. |
| 1.09 | Sitemap XML | Existe, responde 200, solo contiene URLs 200 indexables y canónicas, no incluye noindex ni redirecciones. |
| 1.10 | hreflang | Si el sitio es multidioma: cada versión apunta a la otra (recíproco), códigos válidos (`es`, `en`, `es-CO`), x-default, URLs 200. Si no es multidioma: `no_aplica`. |
| 1.11 | Contenido duplicado | Páginas con el mismo hash de texto o title+description idénticos (variantes con parámetros, http/https, con y sin barra). |
| 1.12 | Páginas huérfanas | URLs del sitemap que ninguna página rastreada enlaza. |
| 1.13 | Enlaces internos rotos | Ya cubierto en 1.01 para destinos; aquí reporta el total de enlaces rotos y las páginas con más enlaces rotos. |
| 1.14 | Datos estructurados | JSON-LD presente donde corresponde (Organization/LocalBusiness en home, Product en tiendas, Article en blog, FAQ si aplica), y JSON válido. No puedes ejecutar la Rich Results Test, así que reporta errores de sintaxis y tipos faltantes, no "elegibilidad". |

### Rendimiento y velocidad

| ID | Chequeo | Cómo |
|---|---|---|
| 1.20 | Tiempo de carga móvil y escritorio | Performance score y Speed Index de PSI por plantilla. |
| 1.21 | Core Web Vitals | Datos de campo (CrUX) de LCP, INP y CLS si existen; si no hay datos de campo (sitio con poco tráfico), usa los de laboratorio y dilo. Umbrales "bueno": LCP ≤ 2,5 s, INP ≤ 200 ms, CLS ≤ 0,1. |
| 1.22 | TTFB | De PSI (`server-response-time`) y del rastreo (`ttfb_ms`). > 800 ms es problema. |
| 1.23 | Imágenes pesadas | Oportunidades de PSI (imágenes sin comprimir, sin formato moderno, sin dimensiones) y las imágenes más pesadas del rastreo. |
| 1.24 | Recursos que bloquean y scripts innecesarios | `render-blocking-resources`, `unused-javascript`, terceros pesados (chats, píxeles, sliders). Nombra el script. |
| 1.25 | Diferencias entre plantillas y dispositivos | Tabla plantilla × dispositivo; señala la plantilla más lenta. |
| 1.26 | Comparación mensual | La hace el gerente con tus `metricas`, pero si ves un cambio grande obvio (por ejemplo un script nuevo de terceros), menciónalo. |

## Métricas a reportar

`paginas_rastreadas`, `errores_4xx`, `errores_5xx`, `redirecciones_internas`, `cadenas_redireccion`, `titles_faltantes`, `titles_duplicados`, `descriptions_faltantes`, `paginas_sin_h1`, `paginas_huerfanas`, `enlaces_rotos`, `urls_sitemap`, `psi_movil_home`, `psi_escritorio_home`, `lcp_movil_home_ms`, `inp_movil_home_ms`, `cls_movil_home`, `ttfb_home_ms`.

## Según la plataforma

- **Framer**: el sitemap y robots los genera Framer; los problemas suelen ser páginas de CMS sin title/description propios, imágenes enormes subidas sin optimizar y animaciones que afectan CLS/INP.
- **Shopify**: URLs duplicadas `/collections/x/products/y` vs `/products/y` son normales si el canonical apunta bien; no las reportes como duplicado si es así. Apps de terceros suelen ser los scripts más pesados.
- **WordPress**: plugins de SEO (Yoast, Rank Math) definen metas y sitemap; plugins de constructores (Elementor, Divi) suelen ser la causa de JS/CSS bloqueante.
- **Astro / código propio**: suele ser rápido; revisa sobre todo metas, sitemap (a veces no existe) y canonical.
