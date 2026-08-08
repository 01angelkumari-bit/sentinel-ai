from __future__ import annotations

import json
from typing import Protocol
from urllib import error, request

from app.core.config import get_settings


class AIModelProvider(Protocol):
    def complete(self, question: str, fallback: str, history: list[dict[str, str]], verified_context: str | None = None) -> str: ...


class LocalHuggingFaceProvider:
    """OpenAI-compatible adapter for a locally hosted Hugging Face text-generation server."""

    def complete(self, question: str, fallback: str, history: list[dict[str, str]], verified_context: str | None = None) -> str:
        settings = get_settings()
        if settings.ai_provider != "local_hf" or not settings.ai_base_url:
            return fallback
        system = "You are Sentinel AI. Respond naturally. Never invent business facts or numbers."
        if verified_context:
            system += f" Use only this verified context for business claims:\n{verified_context}"
        payload = {"model": settings.ai_model_id, "temperature": .2, "max_tokens": 500, "messages": [{"role": "system", "content": system}, *history[-6:], {"role": "user", "content": question}]}
        try:
            req = request.Request(settings.ai_base_url.rstrip("/") + "/v1/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
            with request.urlopen(req, timeout=settings.ai_request_timeout_seconds) as response:
                result = json.loads(response.read())["choices"][0]["message"]["content"].strip()
                return result or fallback
        except (error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
            return fallback


def get_model_provider() -> AIModelProvider:
    return LocalHuggingFaceProvider()
