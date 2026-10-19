"""Cliente OpenAI-compatible para Jan 0.8.6 y modelos Meta Llama."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import httpx


class JanClient:
    def __init__(self):
        self.base_url = os.getenv("JAN_API_URL", "http://host.docker.internal:1337/v1").rstrip("/")
        self.model = os.getenv("JAN_MODEL", "llama-3.1-8b-instruct")
        self.api_key = os.getenv("JAN_API_KEY", "jan-local")
        self.timeout = float(os.getenv("JAN_TIMEOUT", "120"))

    async def chat(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "stream": False,
        }
        if json_mode:
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
