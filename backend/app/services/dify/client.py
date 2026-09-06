from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import get_settings


class DifyError(RuntimeError):
    pass


def _auth_and_workflow(workflow_env: str) -> tuple[str, str | None]:
    """Return (api_key, workflow_id). If workflow_env is app-* treat as dedicated key."""
    settings = get_settings()
    value = (workflow_env or "").strip()
    if value.startswith("app-"):
        return value, None
    key = (settings.dify_api_key or "").strip()
    if not key:
        raise DifyError("DIFY_API_KEY is empty")
    if not value:
        raise DifyError("Dify workflow id is empty")
    return key, value


def dify_available_for(workflow_env: str) -> bool:
    settings = get_settings()
    value = (workflow_env or "").strip()
    if value.startswith("app-"):
        return True
    return bool(settings.dify_api_key and value)


async def run_workflow_blocking(
    workflow_env: str,
    inputs: dict[str, Any],
    *,
    user: str = "banana-agents",
) -> dict[str, Any]:
    settings = get_settings()
    api_key, workflow_id = _auth_and_workflow(workflow_env)
    base = settings.dify_base_url.rstrip("/")
    url = f"{base}/workflows/run"
    payload: dict[str, Any] = {
        "inputs": inputs,
        "response_mode": "blocking",
        "user": user,
    }
    if workflow_id:
        payload["workflow_id"] = workflow_id

    async with httpx.AsyncClient(timeout=settings.job_timeout_sec) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        if resp.status_code >= 400:
            raise DifyError(f"Dify error {resp.status_code}: {resp.text[:500]}")
        return resp.json()


async def run_workflow_streaming(
    workflow_env: str,
    inputs: dict[str, Any],
    *,
    user: str = "banana-agents",
) -> AsyncIterator[str]:
    """Yield text token fragments from Dify SSE workflow run."""
    settings = get_settings()
    api_key, workflow_id = _auth_and_workflow(workflow_env)
    base = settings.dify_base_url.rstrip("/")
    url = f"{base}/workflows/run"
    payload: dict[str, Any] = {
        "inputs": inputs,
        "response_mode": "streaming",
        "user": user,
    }
    if workflow_id:
        payload["workflow_id"] = workflow_id

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise DifyError(f"Dify stream error {resp.status_code}: {body[:500]!r}")
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                event_type = event.get("event")
                if event_type in {"text_chunk", "agent_message", "message"}:
                    data = event.get("data") or event
                    text = data.get("text") or data.get("answer") or ""
                    if text:
                        yield text
                elif event_type == "workflow_finished":
                    outputs = (event.get("data") or {}).get("outputs") or {}
                    for key in ("text", "answer", "result", "content"):
                        if outputs.get(key):
                            # already streamed usually; skip duplicate
                            break
                elif event_type == "error":
                    raise DifyError(str(event.get("data") or event))


def extract_text_output(result: dict[str, Any]) -> str:
    """Best-effort extract text from Dify blocking response."""
    data = result.get("data") or result
    outputs = data.get("outputs") or {}
    for key in ("text", "answer", "result", "content", "architecture", "blueprint", "summary"):
        val = outputs.get(key)
        if isinstance(val, str) and val.strip():
            return val
    if isinstance(outputs, dict) and outputs:
        # join string values
        parts = [str(v) for v in outputs.values() if isinstance(v, str) and v.strip()]
        if parts:
            return "\n".join(parts)
    answer = data.get("answer")
    if isinstance(answer, str):
        return answer
    return json.dumps(outputs or data, ensure_ascii=False)
