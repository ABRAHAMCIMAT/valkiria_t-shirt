# Uso desde Jan por MCP (modelo servido por Ollama)

El backend llama a Meta Llama a través de la API OpenAI-compatible de Ollama.
Jan es opcional: sirve como cliente de chat para usar las herramientas MCP del
proyecto.

1. Inicia Ollama con el modelo descargado:
   `ollama pull llama3.1:8b-instruct-q4_K_M` y `ollama serve`.
2. Inicia el backend en el puerto `8000` con las variables `LLM_*` de
   `.env.example`.
3. En Jan, **Settings → Model Providers**, agrega un proveedor OpenAI-compatible
   con Base URL `http://127.0.0.1:11434/v1` (cualquier API key) y el modelo
   `llama3.1:8b-instruct-q4_K_M`. Activa la capacidad **Tools** del modelo.
4. En **Settings → MCP Servers** agrega el contenido de `mcp-config.json`,
   reemplazando `/RUTA/AL/REPO` por la ruta absoluta del repositorio. Usa el
   Python del entorno virtual (`backend/venv/bin/python`), que tiene instalado
   el paquete `mcp`.
5. Sube el timeout de herramientas MCP a 300 s: `analizar_proyecto` hace varias
   llamadas al modelo.
6. Reinicia Jan y, en un chat con el modelo de Ollama, usa las herramientas para
   consultar el RAG, analizar, editar roles y exportar el Excel.

Los datos del Excel y el modelo permanecen locales; no se requiere una API de nube.
