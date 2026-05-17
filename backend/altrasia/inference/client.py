from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from altrasia.inference.mock_llm import mock_chat_completion


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
            return await mock_chat_completion(messages, tools)
        assert self.base_url
        payload: dict[str, Any] = {"model": self.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            r.raise_for_status()
            return r.json()

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
                "POST", f"{self.base_url}/v1/chat/completions", json=payload
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
