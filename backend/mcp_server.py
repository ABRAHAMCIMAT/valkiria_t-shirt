"""Servidor MCP para usar la solución directamente desde Jan 0.8.6."""

import os
from pathlib import Path
from typing import Any, Dict

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("ESTIMATION_API_URL", "http://127.0.0.1:8000").rstrip("/")
mcp = FastMCP("estimacion-epicas")


def request(method: str, path: str, **kwargs) -> Any:
    with httpx.Client(timeout=180) as client:
        response = client.request(method, f"{API_URL}{path}", **kwargs)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        return response.json() if "json" in content_type else response.content


@mcp.tool()
def preguntar_estimador(pregunta: str) -> Dict[str, Any]:
    """Pregunta al sistema multiagente usando el Excel como conocimiento RAG."""
    return request("POST", "/agent/chat", json={"message": pregunta})


@mcp.tool()
def analizar_proyecto() -> Dict[str, Any]:
    """Analiza épicas, cuestionario, costos y roles; devuelve el dashboard."""
    return request("POST", "/project/analyze")


@mcp.tool()
def listar_roles() -> Dict[str, Any]:
    """Lista roles, colaboradores y costos por hora editables."""
    return request("GET", "/roles")


@mcp.tool()
def crear_rol(nombre: str, costo_hora: float, area: str = "", colaboradores: float = 1) -> Dict[str, Any]:
    """Agrega un rol al modelo de costos."""
    return request("POST", "/roles", json={
        "name": nombre,
        "area": area,
        "required": True,
        "collaborators": colaboradores,
        "cost_hourly": costo_hora,
        "source_cost": costo_hora,
        "source_basis": "hora",
    })


@mcp.tool()
def actualizar_rol(nombre_actual: str, nombre: str, costo_hora: float, area: str = "", colaboradores: float = 1) -> Dict[str, Any]:
    """Modifica nombre, área, cantidad o costo por hora de un rol existente."""
    return request("PUT", f"/roles/{nombre_actual}", json={
        "name": nombre,
        "area": area,
        "required": True,
        "collaborators": colaboradores,
        "cost_hourly": costo_hora,
        "source_cost": costo_hora,
        "source_basis": "hora",
    })


@mcp.tool()
def exportar_excel(carpeta_destino: str = ".") -> Dict[str, str]:
    """Exporta el template completo después de ejecutar analizar_proyecto."""
    data = request("POST", "/export/excel")
    destination = Path(carpeta_destino).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "estimacion_epicas_completa.xlsx"
    output.write_bytes(data)
    return {"archivo": str(output)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
