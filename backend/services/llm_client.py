"""Cliente OpenAI-compatible para modelos Meta Llama servidos por Ollama.

Funciona con cualquier servidor OpenAI-compatible (Ollama, Jan, llama.cpp).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx


def _env(name: str, default: str) -> str:
    """Lee LLM_<name>; acepta JAN_<name> por compatibilidad con configuraciones previas."""
    value: Optional[str] = os.getenv(f"LLM_{name}") or os.getenv(f"JAN_{name}")
    return value or default


class LLMClient:
    def __init__(self):
        self.base_url = _env("API_URL", "http://127.0.0.1:11434/v1").rstrip("/")
        self.model = _env("MODEL", "llama3.1:8b-instruct-q4_K_M")
        self.api_key = _env("API_KEY", "ollama")
        self.timeout = float(_env("TIMEOUT", "300"))

    async def chat(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        json_mode: bool = False,
        schema: Optional[Dict[str, Any]] = None,
    ) -> str:
        """schema restringe la respuesta a ese JSON Schema (structured outputs)."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": False,
        }
        if schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "respuesta", "schema": schema},
            }
        elif json_mode:
            payload["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    async def available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                return response.is_success
        except httpx.HTTPError:
            return False

    @staticmethod
    def parse_json(content: str) -> Dict[str, Any]:
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0]
        return json.loads(content)
