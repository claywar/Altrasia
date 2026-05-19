from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from altrasia.inference.mock_llm import mock_chat_completion
from altrasia.inference.openai_compat import chat_completions_url
from altrasia.inference.tool_calls import normalize_assistant_message
from altrasia.orchestrator.chat_messages import thinking_safe_chat_messages

_THINKING_PREFILL_MARKERS = ("enable_thinking", "assistant response prefill")


class LlmClient:
    def __init__(
        self,
        *,
        base_url: str | None,
        model: str,
        mock: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.model = model
        self.mock = mock or not self.base_url

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if self.mock:
            data = await mock_chat_completion(messages, tools)
        else:
            assert self.base_url
            safe_messages = thinking_safe_chat_messages(messages)
            payload: dict[str, Any] = {"model": self.model, "messages": safe_messages}
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(chat_completions_url(self.base_url), json=payload)
                if r.status_code == 400 and any(
                    m in (r.text or "").lower() for m in _THINKING_PREFILL_MARKERS
                ):
                    payload["messages"] = thinking_safe_chat_messages(messages)
                    r = await client.post(chat_completions_url(self.base_url), json=payload)
                r.raise_for_status()
                data = r.json()
        choice = data["choices"][0]
        choice["message"] = normalize_assistant_message(choice.get("message") or {})
        return data

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str]:
        if self.mock:
            result = await mock_chat_completion(messages, None)
            text = result["choices"][0]["message"].get("content", "")
            for word in text.split():
                yield word + " "
            return
        assert self.base_url
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", chat_completions_url(self.base_url), json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    data = json.loads(chunk)
                    delta = data["choices"][0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
