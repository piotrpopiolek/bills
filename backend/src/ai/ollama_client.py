"""Minimal async client for local Ollama HTTP API."""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Optional

import httpx

from src.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 180.0,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout

    async def chat(
        self,
        *,
        model: str,
        prompt: str,
        images: Optional[list[bytes]] = None,
        format_schema: Optional[dict[str, Any] | str] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        Call Ollama /api/chat and return assistant message content as text.
        """
        message: dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            message["images"] = [
                base64.b64encode(img).decode("ascii") for img in images
            ]

        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "messages": [message],
            "options": {"temperature": temperature},
        }
        if format_schema is not None:
            payload["format"] = format_schema

        url = f"{self.base_url}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                if response.is_error:
                    detail = response.text
                    try:
                        detail = response.json().get("error", detail)
                    except Exception:
                        pass
                    logger.error(
                        "Ollama HTTP %s: %s",
                        response.status_code,
                        detail,
                    )
                    response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.error("Ollama request failed: %s", e, exc_info=True)
            raise

        content = (data.get("message") or {}).get("content")
        if not content:
            raise ValueError(f"Empty Ollama response: {data!r}")
        return content

    async def chat_json(
        self,
        *,
        model: str,
        prompt: str,
        images: Optional[list[bytes]] = None,
        format_schema: Optional[dict[str, Any] | str] = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        text = await self.chat(
            model=model,
            prompt=prompt,
            images=images,
            format_schema=format_schema if format_schema is not None else "json",
            temperature=temperature,
        )
        # Some models wrap JSON in markdown fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
