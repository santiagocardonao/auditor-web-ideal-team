# Entregables

Cuando `informe.json` esté listo, pregunta: **"¿Prefieres el informe en PDF o como dashboard en React (artefacto)?"**. Ambos salen del mismo `informe.json`, así que si luego piden el otro formato no hay que reauditar.

## Estructura del contenido (igual para ambos)

1. **Portada / encabezado**: cliente, sitio, periodo, plataforma, fecha de la auditoría.
2. **Resumen ejecutivo**: 3-5 frases. Qué está bien, qué es lo urgente, qué cambió desde el mes pasado.
3. **Puntaje por área**: las 8 áreas (SEO técnico, Rendimiento, Contenido, UX, Orgánico, Conversión, Seguridad, Medición) en una fila de tarjetas con semáforo (≥ 80 verde, 50-79 amarillo, < 50 rojo, N/D gris).
4. **Top prioridades**: 5-10 hallazgos, cada uno con qué pasa, por qué importa, qué hacer y esfuerzo.
5. **Comparación con el mes anterior**: métricas que mejoraron y que empeoraron (si hay mes anterior; si no, "Primera auditoría: línea base").
6. **Hallazgos por área**: tabla completa agrupada por área, con severidad, evidencia y recomendación.
7. **Próximo mes**: landings, contenidos, mejoras SEO y experimentos propuestos.
8. **No evaluado**: qué no se revisó y qué acceso hace falta para revisarlo el mes que viene.
9. **Aviso**: "Este informe no sustituye una auditoría de ciberseguridad."

Escribe para alguien de la agencia o del cliente que no es técnico: "6 enlaces del menú llevan a páginas que no existen" en vez de "6 hrefs internos con status 404".

## PDF

```bash
python3 <skill>/scripts/generar_pdf.py auditorias/<dominio>/<AAAA-MM>/informe.json --salida auditorias/<dominio>/<AAAA-MM>/informe-<dominio>-<AAAA-MM>.pdf
```

El script arma un HTML con `assets/plantilla-informe.html` y lo convierte a PDF con Google Chrome en modo headless (o Chromium / Edge si no hay Chrome). Si no encuentra ningún navegador, deja el HTML y avisa: se puede abrir y usar "Imprimir → Guardar como PDF".

Si el usuario tiene un logo de la agencia, pásalo con `--logo ruta.png`. Revisa el PDF generado (ábrelo o conviértelo a imagen) antes de entregarlo.

## Dashboard en React (artefacto)

Publica un artefacto con la herramienta Artifact del entorno (carga antes las guías de diseño de artefactos que el entorno indique). Requisitos:

- Los datos de `informe.json` van **embebidos** en el código del artefacto (un `const INFORME = {...}`), no cargados de una URL externa.
- React desde un CDN permitido, con versión exacta.
- Vista: encabezado con cliente y periodo, tarjetas de puntaje por área, lista de prioridades, filtros por área y severidad sobre la tabla de hallazgos, bloque de comparación mensual (flechas ↑↓ y variación) y sección de no evaluado.
- Funciona en móvil y en modo oscuro.
- El artefacto es privado por defecto. No lo compartas ni lo publiques más allá sin que el usuario lo pida: contiene datos del cliente.

Si el entorno no tiene herramienta de artefactos (por ejemplo, Claude Code en terminal sin ella), genera un único archivo `dashboard-<dominio>-<AAAA-MM>.html` autocontenido con React por CDN y avisa dónde quedó.
