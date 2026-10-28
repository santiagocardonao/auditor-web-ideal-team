# Formato de hallazgos

Todos los agentes escriben el mismo formato para que el gerente pueda consolidar sin traducir nada.

## agente-N.json

```json
{
  "agente": "1-tecnico-rendimiento",
  "sitio": "https://dominio.com",
  "fecha": "2026-10-28",
  "plataforma": "wordpress",
  "accesos_usados": ["rastreo", "pagespeed"],
  "metricas": {
    "paginas_rastreadas": 214,
    "errores_404": 6,
    "lcp_movil_p75_ms": 3100
  },
  "chequeos": [
    {
      "id": "1.01",
      "area": "SEO técnico",
      "nombre": "Errores 404",
      "estado": "evaluado",
      "resultado": "problema",
      "motivo_no_evaluado": null
    },
    {
      "id": "1.07",
      "area": "SEO técnico",
      "nombre": "Páginas indexadas y motivos de exclusión",
      "estado": "no_evaluado",
      "resultado": null,
      "motivo_no_evaluado": "Sin acceso a Google Search Console"
    }
  ],
  "hallazgos": [
    {
      "id": "1.01-a",
      "chequeo": "1.01",
      "titulo": "6 enlaces internos llevan a páginas 404",
      "severidad": "alta",
      "impacto": "Usuarios y Google llegan a páginas rotas desde el menú y el blog",
      "evidencia": "https://dominio.com/servicios-old (enlazada desde /, /blog/x)",
      "urls": ["https://dominio.com/servicios-old"],
      "recomendacion": "Redirigir 301 a /servicios o corregir el enlace en el menú",
      "esfuerzo": "bajo"
    }
  ]
}
```

### Campos

- `estado`: `evaluado` | `no_evaluado` | `no_aplica` (por ejemplo, hreflang en un sitio de un solo idioma).
- `resultado`: `ok` | `advertencia` | `problema` (solo si se evaluó).
- `severidad`:
  - `critica`: rompe conversión, indexación o seguridad ahora mismo (formulario de contacto caído, sitio con noindex, certificado vencido, malware visible).
  - `alta`: pérdida clara de tráfico o leads (404 en páginas enlazadas, LCP > 4 s en móvil en la home, caída fuerte de clics).
  - `media`: afecta pero no urge (metas duplicadas, imágenes pesadas en páginas secundarias).
  - `baja`: pulido.
- `esfuerzo`: `bajo` (minutos u horas), `medio` (días), `alto` (proyecto).
- `evidencia`: siempre algo verificable: URL, valor medido, fragmento de texto, nombre de archivo de captura. Nunca "parece que".

Usa el mismo `id` de chequeo cada mes (están numerados en cada manual) para que la comparación entre meses funcione.

`metricas` son números planos (sin anidar) que el gerente compara mes a mes. Usa los nombres sugeridos en cada manual.

## informe.json (lo escribe el gerente)

```json
{
  "sitio": "https://dominio.com",
  "cliente": "Nombre del cliente",
  "periodo": "2026-10",
  "plataforma": "wordpress",
  "resumen_ejecutivo": "3-5 frases: estado general, lo más urgente, lo que mejoró.",
  "puntaje_por_area": {"SEO técnico": 72, "Rendimiento": 55},
  "top_prioridades": ["1.01-a", "3.04-b", "2.12-a"],
  "hallazgos": [ "...todos los hallazgos consolidados, ordenados por prioridad..." ],
  "no_evaluado": [{"chequeo": "1.07", "nombre": "...", "motivo": "..."}],
  "comparacion_mes_anterior": { "...contenido de comparacion.json o null..." },
  "proximo_mes": [
    {"tipo": "landing", "titulo": "...", "por_que": "..."},
    {"tipo": "experimento", "titulo": "...", "por_que": "..."}
  ],
  "aviso": "Este informe no sustituye una auditoría de ciberseguridad."
}
```

### Puntaje por área (0-100)

Parte de 100 y resta por cada hallazgo del área: crítica −25, alta −10, media −4, baja −1, con mínimo 0. Si en un área hay más de la mitad de los chequeos sin evaluar, muestra "N/D" en lugar del puntaje: un número basado en pocos datos engaña.
