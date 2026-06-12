from __future__ import annotations

import logging

import httpx

from bot.config import Settings

log = logging.getLogger(__name__)


async def call_llm(
    settings: Settings,
    messages: list[dict],
    tools: list[dict] | None = None,
    tool_choice: str = "auto",
) -> dict:
    """Call the LLM with optional tool definitions.

    Returns the full ``message`` dict from the first choice, which may
    contain ``content``, ``tool_calls``, or both.

    Raises ``httpx.HTTPStatusError`` on non-2xx responses so callers can
    decide how to handle API failures.
    """
    payload: dict = {
        "model": settings.model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2048,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        resp = await client.post(
            settings.deepseek_base_url,
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()

    msg = data["choices"][0]["message"]
    finish = data["choices"][0].get("finish_reason", "")
    usage = data.get("usage", {})

    log.info(
        "LLM call done: finish=%s, tokens=%s, tool_calls=%d",
        finish,
        usage.get("total_tokens", "?"),
        len(msg.get("tool_calls") or []),
    )

    return msg
