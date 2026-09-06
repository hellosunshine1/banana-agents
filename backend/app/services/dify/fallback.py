from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from app.services.dify.client import dify_available_for


def use_dify(workflow_env: str) -> bool:
    from app.config import get_settings

    mode = (get_settings().generation_backend or "auto").lower()
    if mode == "dify":
        return dify_available_for(workflow_env)
    if mode == "langchain":
        return False
    return dify_available_for(workflow_env)


def _client_from_preset(preset: dict[str, Any]) -> tuple[AsyncOpenAI, str]:
    api_key = (preset.get("api_key") or "").strip()
    if not api_key:
        raise ValueError("LLM api_key is empty; configure it in Settings")
    base_url = (preset.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = preset.get("model_name") or "gpt-4o-mini"
    timeout = float(preset.get("timeout") or 600)
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
    return client, model


async def chat_complete(preset: dict[str, Any], prompt: str, *, system: str = "") -> str:
    client, model = _client_from_preset(preset)
    temperature = float(preset.get("temperature") or 0.7)
    max_tokens = int(preset.get("max_tokens") or 4096)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


async def chat_stream(preset: dict[str, Any], prompt: str, *, system: str = "") -> AsyncIterator[str]:
    client, model = _client_from_preset(preset)
    temperature = float(preset.get("temperature") or 0.7)
    max_tokens = int(preset.get("max_tokens") or 4096)
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta
