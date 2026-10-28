# Auditor-Web-Ideal-Team

Skill para Claude que **analiza entre varios agentes los sitios web que administra la agencia**. Reemplaza la revisión manual que el equipo hace cada 15 días o a fin de mes.

Funciona como un auditor profesional con perfil full-stack (SEO, construcción web y negocio). Un **auditor gerente** prepara la auditoría y delega en 4 agentes especialistas. Después consolida todo en un informe priorizado, en **PDF** o como **dashboard en React**.

## Cómo funciona

```
                    ┌──────────────────────────┐
                    │      Auditor gerente      │
                    │ plataforma · accesos ·    │
                    │ rastreo · consolida       │
                    └────────────┬─────────────┘
       ┌───────────────┬─────────┴─────┬────────────────┐
       ▼               ▼               ▼                ▼
 1. Técnico y     2. Contenido y   3. Conversión,   4. Seguridad
    rendimiento      orgánico         UX y medición    y confianza
```

| Agente | Revisa | Accesos que pide |
|---|---|---|
| 1. Técnico y rendimiento | 404, redirecciones, metas, encabezados, canonical, hreflang, robots, sitemap, indexación, duplicados, huérfanas, enlaces rotos, datos estructurados, velocidad, Core Web Vitals | API key de PageSpeed Insights; Search Console opcional |
| 2. Contenido y orgánico | Ortografía y traducciones (ES/EN), contenido escaso o repetido, coherencia título/intención/CTA, clics, impresiones, CTR, posición, páginas que caen, canibalización, oportunidades | Search Console (CSV o API) |
| 3. Conversión, UX y medición | Menús, botones, formularios, buscador, CTA, móvil/tablet/escritorio, accesibilidad básica, recorridos críticos, propuesta de valor, anuncio→landing, GA4, GTM, eventos | Navegador; GA4/GTM y textos de anuncios opcionales |
| 4. Seguridad y confianza | HTTPS, certificado, contenido mixto, headers, avisos legales, enlaces sospechosos, señales de confianza, versiones expuestas | Ninguno; panel o servidor opcional (WordPress) |

Los agentes se agrupan por tipo de acceso. Así cada uno pide un solo paquete de permisos.

### Flujo

1. **Sitio y carpeta**: crea `auditorias/<dominio>/<AAAA-MM>/`.
2. **Plataforma**: detecta si es WordPress, Framer, Shopify, Astro, Webflow, Wix o código propio.
3. **Accesos**: pregunta qué accesos tiene la persona que corre la auditoría. Nada es obligatorio: lo que no se puede revisar queda como **"No evaluado: falta acceso a X"**.
4. **Rastreo base**: un solo rastreo del sitio que comparten los agentes.
5. **Agentes en paralelo**: cada uno escribe sus hallazgos en el mismo formato.
6. **Consolidación**: quita duplicados, prioriza y compara con el mes anterior.
7. **Entregable**: pregunta si lo quieres en PDF o como dashboard en React.

## Instalación

### Claude Code

```bash
git clone https://github.com/santiagocardonao/auditor-web-ideal-team.git ~/.claude/skills/auditor-web-ideal-team
```

Abre una sesión nueva de Claude Code y pide, por ejemplo: *"Haz la auditoría mensual de https://cliente.com"*.

### Claude.ai / Claude Desktop

Descarga `auditor-web-ideal-team.skill` desde [Releases](../../releases) e instálalo en Configuración → Capacidades → Skills. En claude.ai no hay subagentes, así que los 4 agentes corren uno tras otro, y el rastreo depende de que el entorno tenga acceso a internet.

## Requisitos

- **Python 3.9+**. Los scripts solo usan la librería estándar.
- **Google Chrome, Chromium o Edge** para convertir el informe a PDF. Sin navegador queda el HTML para imprimirlo a mano.
- **API key de PageSpeed Insights** (gratis en Google Cloud), como variable de entorno `PSI_API_KEY`. Sin ella, la cuota compartida casi siempre está agotada.
- Opcional, para Search Console por API: `pip install google-api-python-client google-auth` y una cuenta de servicio con permiso de lectura sobre la propiedad.

## Uso

Ejemplos de lo que se le puede pedir:

- "Auditoría mensual de https://cliente.com"
- "Revisa solo la velocidad y los 404 de tienda.com"
- "¿Están funcionando los formularios y el tracking de GA4 en cliente.com?"
- "Compara la auditoría de este mes de cliente.com con la del mes pasado"

Cada auditoría queda guardada así:

```
auditorias/cliente.com/2026-10/
├── rastreo.json          # rastreo base
├── agente-1.json … agente-4.json
├── resumen.json          # métricas del mes (para comparar)
├── comparacion.json      # vs mes anterior
├── informe.json          # consolidado
├── capturas/
└── informe-cliente.com-2026-10.pdf
```

Para la comparación mensual, conserva la carpeta `auditorias/` entre meses.

## Scripts

| Script | Qué hace |
|---|---|
| `detectar_plataforma.py` | Detecta la plataforma por firmas en HTML y headers |
| `rastrear.py` | Rastreo de solo lectura: respeta robots.txt, sigue el sitemap, extrae metas, encabezados, enlaces, imágenes, scripts, JSON-LD, formularios y etiquetas de medición |
| `analizar_rastreo.py` | Calcula 404, redirecciones, duplicados, huérfanas, canonical, hreflang, sitemap y plantillas a medir |
| `pagespeed.py` | PageSpeed Insights en móvil y escritorio: datos de campo (CrUX), de laboratorio y oportunidades |
| `gsc.py` | Analiza Search Console desde CSV o API: variaciones, CTR bajo, páginas que caen, canibalización y oportunidades |
| `seguridad.py` | Chequeos pasivos: redirecciones, certificado, headers, contenido mixto, enlaces sospechosos, avisos legales, rutas expuestas |
| `comparar_meses.py` | Arma `resumen.json` y la comparación con el mes anterior |
| `generar_pdf.py` | Genera el informe en PDF a partir de `informe.json` |

## Límites y reglas

- **Solo lectura.** La skill no cambia nada en los sitios, en Search Console, en GA4 ni en los servidores.
- **Los formularios no se envían** sin autorización explícita, porque crearían leads falsos para el cliente. Tampoco se completan compras.
- **Seguridad pasiva.** No hace escaneos de vulnerabilidades ni pruebas intrusivas, y **no sustituye una auditoría de ciberseguridad**.
- **Indexación.** La API de Search Console no entrega el informe completo de indexación. Para sitios grandes conviene exportarlo en CSV.
- **Bloqueos.** Algunos sitios detrás de Cloudflare o Shopify bloquean rastreadores (403/429). En ese caso se sube la pausa o se pide permitir la IP.
- **Confidencialidad.** Las credenciales nunca se piden en el chat ni se guardan en la carpeta de la auditoría. Los informes contienen datos de clientes: no los subas a este repositorio (`auditorias/` está en `.gitignore`).

## Estructura del repositorio

```
auditor-web-ideal-team/
├── SKILL.md                     # el auditor gerente
├── references/
│   ├── agente-1-tecnico-rendimiento.md
│   ├── agente-2-contenido-organico.md
│   ├── agente-3-conversion-ux-medicion.md
│   ├── agente-4-seguridad-confianza.md
│   ├── formato-hallazgos.md     # formato común de resultados
│   └── entregables.md           # PDF y dashboard
├── scripts/
└── assets/plantilla-informe.html
```
