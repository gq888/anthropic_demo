"""LLM client wrapper around an OpenAI-compatible API."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from app.core.settings import Settings, get_settings


class LLMClient:
    """Thin async client handling auth, retries, and future streaming support."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self._settings = settings or get_settings()
        self._client = httpx.AsyncClient(
            base_url=str(self._settings.openai_base_url),
            headers={
                "Authorization": f"Bearer {self._settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model or self._settings.openai_model,
            "temperature": temperature or self._settings.openai_temperature,
            "max_tokens": max_tokens or self._settings.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt or "You are a helpful research agent."},
                {"role": "user", "content": prompt},
            ],
        }

        for attempt in range(3):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                raise HTTPException(status_code=502, detail="LLM upstream error") from exc
            except httpx.RequestError as exc:
                if attempt < 2:
                    await asyncio.sleep(2**attempt)
                    continue
                raise HTTPException(status_code=504, detail="LLM request failed") from exc

        raise HTTPException(status_code=500, detail="LLM request exhausted retries")
