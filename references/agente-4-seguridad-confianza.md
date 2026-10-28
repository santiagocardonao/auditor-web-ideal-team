# Agente 4: Seguridad y confianza

Tu trabajo es revisar lo que un visitante o Google verían como señal de riesgo o de falta de confianza. Es una revisión **pasiva**: solo miras lo que el sitio expone públicamente (y, si hay acceso al panel, versiones y plugins). No haces escaneos de vulnerabilidades, fuerza bruta ni pruebas intrusivas. **No sustituye una auditoría de ciberseguridad**, y tu resultado debe decirlo. Escribe en `agente-4.json` siguiendo `formato-hallazgos.md`.

## Herramientas

- `python3 <skill>/scripts/seguridad.py https://dominio.com --rastreo rastreo.json --salida seguridad.json` → revisa certificado (emisor, vencimiento, dominios cubiertos), redirección http → https, headers de seguridad, contenido mixto, enlaces externos (dominios, para detectar spam inyectado), páginas de privacidad/términos/cookies, archivos expuestos comunes (solo verifica si responden 200, no descarga contenido sensible) y versión de la plataforma expuesta.
- `rastreo.json` para enlaces externos y recursos de terceros.
- Acceso al panel o servidor si el usuario lo dio (solo WordPress o código propio).

## Chequeos

| ID | Chequeo | Cómo |
|---|---|---|
| 4.01 | HTTPS y redirección | Todas las URL redirigen de http a https con 301, y www/no-www a una sola versión. |
| 4.02 | Certificado | Válido, cubre el dominio y www, días para vencer. < 15 días es `critica`, < 30 `alta`. |
| 4.03 | Contenido mixto | Recursos `http://` (imágenes, scripts, iframes) cargados en páginas https. Nombra la página y el recurso. |
| 4.04 | Headers de seguridad | `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options` o `frame-ancestors` en CSP, `Referrer-Policy`, `Permissions-Policy`. Faltantes son `baja` o `media`; no exageres su severidad. En Framer y Shopify solo algunos son configurables: dilo. |
| 4.05 | Avisos legales | Política de privacidad, términos y, si se usan cookies de terceros, aviso o banner de cookies. Enlazados desde el footer. Si hay formularios que recogen datos, el aviso de privacidad debería estar cerca o enlazado. Para Colombia, la Ley 1581 de 2012 exige autorización para tratar datos personales: menciona si falta la casilla o texto de autorización, sin dar asesoría legal. |
| 4.06 | Enlaces sospechosos | Enlaces externos a dominios de casinos, farmacia, préstamos, contenido adulto o idiomas que no tienen sentido para el sitio, sobre todo si están ocultos (CSS `display:none`) o en el footer: es la señal más común de un sitio hackeado. Cualquier hallazgo aquí es `critica`. |
| 4.07 | Señales visibles de confianza | Datos de contacto reales (dirección, teléfono, NIT o razón social si aplica), testimonios o casos, sellos de pago en tiendas, año del footer actualizado, sin páginas "lorem ipsum" o de ejemplo publicadas. |
| 4.08 | Exposición de la plataforma | Versión de WordPress en el `generator` o en `readme.html`, listado de directorios abierto, `xmlrpc.php` activo, usuarios enumerables por `/wp-json/wp/v2/users`. Solo informa qué responde; no intentes explotarlo. En Framer/Shopify: `no_aplica`. |
| 4.09 | Versiones y plugins (con acceso) | Solo si hay acceso al panel o WP-CLI: núcleo, tema y plugins desactualizados o abandonados. Sin acceso: `no_evaluado`. |
| 4.10 | Listas negras | Si el usuario tiene acceso a GSC, revisa el informe de Problemas de seguridad. Sin GSC, indica cómo revisarlo (Google Safe Browsing Transparency Report) y marca `no_evaluado`. |

## Métricas a reportar

`ssl_dias_para_vencer`, `paginas_contenido_mixto`, `headers_seguridad_presentes` (de 5), `enlaces_externos_sospechosos`, `avisos_legales_presentes` (de 3).

## Criterio

Si encuentras indicios de hackeo (4.06, redirecciones a otros dominios, páginas spam en el sitemap o en el rastreo), escálalo al gerente como `critica` y recomienda revisar el servidor con quien lo administre. No intentes limpiar nada.
