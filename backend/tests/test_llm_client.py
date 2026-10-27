"""Configuración del cliente LLM (Ollama por defecto) y del servidor MCP."""
import asyncio

import pytest

from services.llm_client import LLMClient

ENV_NAMES = ["API_URL", "MODEL", "API_KEY", "TIMEOUT"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(f"LLM_{name}", raising=False)
        monkeypatch.delenv(f"JAN_{name}", raising=False)


def test_defaults_point_to_local_ollama():
    client = LLMClient()

    assert client.base_url == "http://127.0.0.1:11434/v1"
    assert client.model == "llama3.1:8b-instruct-q4_K_M"
    assert client.timeout == 300


def test_llm_variables_take_precedence_over_jan(monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "llama3.2:3b-instruct-q4_K_M")
    monkeypatch.setenv("JAN_MODEL", "llama-3.1-8b-instruct")

    assert LLMClient().model == "llama3.2:3b-instruct-q4_K_M"


def test_legacy_jan_variables_still_work(monkeypatch):
    monkeypatch.setenv("JAN_API_URL", "http://127.0.0.1:1337/v1/")

    assert LLMClient().base_url == "http://127.0.0.1:1337/v1"


def test_mcp_server_exposes_tools():
    import mcp_server

    tools = {tool.name for tool in asyncio.run(mcp_server.mcp.list_tools())}

    assert {"preguntar_estimador", "analizar_proyecto", "listar_roles", "exportar_excel"} <= tools
