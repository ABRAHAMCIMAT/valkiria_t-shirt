# Arquitectura multiagente

```text
Jan 0.8.6 (Meta Llama) ── OpenAI API :1337 ─┐
Jan Chat ── MCP stdio ──────────────────────┤
                                             ▼
Next.js :3000 ── REST ── FastAPI :8000 ── Orquestador
                                   ├── Estimador ML existente (RF + DT)
                                   ├── Analista RAG (TF-IDF, hoja/fila)
                                   ├── Especialista de costos y roles
                                   ├── Analista de cuestionario (Llama)
                                   └── Revisor senior (Llama)
                                             │
                                             ├── Dashboard JSON
                                             └── Exportación XLSX
```

## Flujo

1. `POST /knowledge/upload` copia el template, extrae filas no vacías e indexa
   su texto. Roles, preguntas/opciones y épicas también se normalizan.
2. El catálogo de roles usa una tarifa por hora editable. Los importes mensuales
   de ejemplo se dividen entre 160 horas; el supuesto siempre se informa.
3. `POST /project/analyze` ejecuta el modelo ensemble existente si está cargado.
   Si todavía no hay modelo entrenado, usa una heurística explícitamente marcada
   para que la aplicación continúe, sin presentar el resultado como ML.
4. Los agentes de Llama eligen únicamente entre opciones reales del
   `Cuestionario`; un error de Jan activa una selección conservadora marcada para
   revisión humana.
5. `POST /export/excel` rellena Roles, Cuestionario, Epic Backlog, Resultado,
   Arquitectura y Proceso To-Be sobre una copia del archivo original.

## Privacidad y operación

El RAG no envía el libro a servicios cloud. Jan y el modelo Llama se ejecutan
localmente. Para producción se recomienda autenticación en FastAPI, cifrado del
directorio `backend/data`, CORS restringido y trazabilidad por usuario.
