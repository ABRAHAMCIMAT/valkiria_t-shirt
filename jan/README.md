# Integración con Jan 0.8.6 y Meta Llama

1. Instala **Jan 0.8.6** desde la publicación indicada y descarga un modelo
   instruct de Meta Llama compatible con tu equipo (por ejemplo, Llama 3.1 8B
   Instruct cuantizado).
2. En Jan activa **Settings → Local API Server**, puerto `1337`, y carga el
   modelo.
3. Copia `.env.example` a `.env` y usa en `JAN_MODEL` el identificador exacto
   mostrado por `GET http://127.0.0.1:1337/v1/models`.
4. Inicia el backend en el puerto `8000`.
5. En la configuración MCP de Jan agrega el contenido de `mcp-config.json`,
   reemplazando `C:/RUTA/...` por la ruta absoluta del repositorio y `python`
   por el ejecutable del entorno virtual si aplica.
6. Reinicia Jan. En el chat estarán disponibles las herramientas para consultar
   el RAG, analizar, editar roles y exportar el Excel.

El backend llama a la API OpenAI-compatible de Jan. Los datos del Excel y el
modelo permanecen locales; no se requiere una API de nube.
