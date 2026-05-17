from __future__ import annotations

import re
from typing import Any

DEFAULT_STRIP_TAGS = (
    "\u003cthink\u003e",
    "\u003c/think\u003e",
    "<|think|>",
    "<|/think|>",
)
DEFAULT_API_FIELDS = ("reasoning_content", "reasoning", "thinking")


def strip_reasoning(content: str, *, strip_tags: tuple[str, ...] = DEFAULT_STRIP_TAGS) -> str:
    """MP-15: Remove reasoning blocks before durable writes."""
    text = content or ""
    for field in DEFAULT_API_FIELDS:
        # Not applicable to plain strings
        pass
    for i in range(0, len(strip_tags), 2):
        if i + 1 >= len(strip_tags):
            break
        open_tag, close_tag = strip_tags[i], strip_tags[i + 1]
        pattern = re.compile(
            re.escape(open_tag) + r"[\s\S]*?" + re.escape(close_tag), re.IGNORECASE
        )
        text = pattern.sub("", text)
    return text.strip()


def strip_from_message_payload(payload: dict[str, Any]) -> str:
    content = payload.get("content") or payload.get("outputText") or ""
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        content = "\n".join(parts)
    text = str(content)
    for field in DEFAULT_API_FIELDS:
        extra = payload.get(field)
        if extra:
            text = text.replace(str(extra), "")
    return strip_reasoning(text)


def is_durable_value_ok(value: str) -> bool:
    """MP-16: reject empty or reasoning-only."""
    return bool(value and value.strip())
