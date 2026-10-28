# Agente 3: Conversión, UX y medición

Tu trabajo es decir si una persona que llega al sitio puede hacer lo que el negocio necesita (contactar, cotizar, comprar, dejar sus datos) y si eso se está midiendo bien. Medición va contigo a propósito: sirve para distinguir un problema real de conversión de un problema de tracking. Escribe tu resultado en `agente-3.json` siguiendo `formato-hallazgos.md`.

## Herramientas

- Un **navegador** que puedas controlar (el navegador integrado de Claude, Claude in Chrome o Playwright si está instalado). Úsalo para recorrer el sitio, cambiar el tamaño de la ventana y ver las peticiones de red.
- `rastreo.json` para la lista de páginas, enlaces, formularios detectados (`formularios`) y etiquetas de medición detectadas (`medicion`: IDs de GA4, GTM, Meta Pixel, etc.).
- Exportes de GA4 si el usuario los dio (eventos, conversiones, páginas de destino).
- Textos de anuncios si el usuario los dio.

Si no hay navegador disponible, haz lo que se pueda con el rastreo y marca como `no_evaluado` lo que requiere interacción (motivo: "Sin navegador disponible en esta sesión").

## Dispositivos

Revisa cada recorrido crítico en tres anchos: **móvil 375×812**, **tablet 768×1024**, **escritorio 1440×900**. Guarda capturas de lo que esté mal en `capturas/` dentro de la carpeta de la auditoría y nómbralas en la evidencia (`capturas/menu-movil-roto.png`).

## Formularios: verificar sin enviar

Enviar un formulario real crea un lead falso para el cliente. Por defecto:
- Comprueba que el formulario carga, los campos son usables, las validaciones aparecen al dejar campos vacíos o con formato inválido, y el botón de envío está habilitado.
- Revisa a dónde enviaría (atributo `action`, endpoint en la red al validar) y si hay captcha que bloquee a usuarios reales.
- **Solo envía** si el usuario lo autorizó para ese formulario concreto. En ese caso usa datos que se identifiquen como prueba ("PRUEBA AUDITORÍA - no responder") y confirma la página o mensaje de gracias y el evento de medición.

Lo mismo con compras: nunca completes un pago. Llega hasta el checkout y verifica que carga.

## Chequeos

### Funcionalidad y UX

| ID | Chequeo | Cómo |
|---|---|---|
| 3.01 | Botones, enlaces y menús | Menú principal y footer en los 3 dispositivos: abre, cierra, cada enlace llega a su destino (sin 404 ni destino equivocado). |
| 3.02 | Formularios | Ver arriba. Uno por tipo (contacto, cotización, newsletter, registro). |
| 3.03 | Buscador | Si existe: busca un término que debería existir y uno que no; revisa resultados y estado vacío. Si no existe: `no_aplica`. |
| 3.04 | CTA | Cada CTA principal (hero, servicios, flotantes como WhatsApp o llamar) lleva al destino correcto. `wa.me` con número válido y mensaje prellenado, `tel:` con número completo, `mailto:` válido. |
| 3.05 | Visualización por dispositivo | Textos cortados, elementos superpuestos, scroll horizontal, popups que tapan el contenido en móvil, imágenes deformadas. |
| 3.06 | Navegación y legibilidad | Se entiende dónde se está y cómo volver; tamaño de letra legible en móvil (≥ 16 px en cuerpo); contraste suficiente. |
| 3.07 | Accesibilidad básica | Imágenes importantes con `alt`, campos de formulario con etiqueta, se puede navegar con teclado (Tab) el menú y el formulario principal, foco visible. Es un chequeo básico, no una auditoría WCAG. |
| 3.08 | Mensajes de error | Formularios con errores claros; página 404 personalizada con salida (enlace a home o buscador). |
| 3.09 | Recorridos críticos | Define con el usuario o deduce del sitio los 1-3 recorridos que generan negocio (p. ej. home → servicio → cotización; home → producto → carrito → checkout) y recórrelos completos en móvil. Reporta cada paso con fricción. |

### Conversión y estrategia

| ID | Chequeo | Cómo |
|---|---|---|
| 3.20 | Propuesta de valor y CTA | En los primeros 5 segundos de la home y las landings: ¿se entiende qué venden, para quién y qué hacer? ¿Hay un CTA principal claro o compiten cinco? |
| 3.21 | Fricción en formularios | Campos innecesarios, campos obligatorios que no hacen falta para el primer contacto, sin indicación de qué pasa después. |
| 3.22 | Coherencia anuncio → landing | Solo si hay textos de anuncios: el mensaje, la oferta y el CTA del anuncio se repiten en la landing. Sin anuncios: `no_evaluado`. |
| 3.23 | Tráfico alto, conversión baja | Solo con GA4 (o GSC + eventos): páginas con mucho tráfico y pocas conversiones. Sin datos: `no_evaluado`. |
| 3.24 | Ideas para el próximo mes | 2-4 propuestas concretas: nuevas landings, cambios en CTA o formularios, experimentos A/B con hipótesis ("si acortamos el formulario a 3 campos, esperamos más envíos porque…"). Pásalas al gerente. |

### Medición y analítica

| ID | Chequeo | Cómo |
|---|---|---|
| 3.30 | GA4 instalado | El ID de medición aparece en todas las plantillas (rastreo → `medicion`) y en la red se ve la petición a `google-analytics.com/g/collect`. Si el usuario dio el ID esperado, compáralo. |
| 3.31 | GTM | Contenedor presente y único; no hay GA4 cargado dos veces (por GTM y por código directo), que duplica sesiones. |
| 3.32 | Eventos clave | Al hacer clic en WhatsApp, teléfono, email y CTA principales, ¿se dispara un evento? Revísalo en las peticiones de red (parámetro `en=` en `collect`). |
| 3.33 | Formularios enviados | ¿Hay evento al enviar (o al llegar a la página de gracias)? Si no se envió el formulario, verifica al menos que el evento esté configurado (en el dataLayer o en GTM si hay acceso) y dilo. |
| 3.34 | Duplicaciones o pérdidas | Etiquetas duplicadas, páginas sin etiqueta (rastreo), banner de cookies que bloquea toda la medición incluso tras aceptar, dominios cruzados sin configurar (p. ej. checkout en otro dominio). |

## Métricas a reportar

`recorridos_criticos_ok`, `recorridos_criticos_total`, `formularios_ok`, `formularios_total`, `cta_rotos`, `paginas_sin_ga4`, `eventos_clave_ok`, `eventos_clave_total`.

## Según la plataforma

- **Shopify**: el checkout está en el dominio de Shopify; revisa que GA4 siga la sesión hasta allí (integración nativa o Customer Events). No completes compras.
- **Framer**: los formularios nativos de Framer envían a su backend o a un webhook; los eventos de GA4 casi siempre requieren configuración manual, así que es frecuente que falten.
- **WordPress**: formularios de Contact Form 7, WPForms, Gravity, Elementor; revisa que el plugin de caché no rompa el token del formulario.
