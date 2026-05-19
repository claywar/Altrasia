from __future__ import annotations

import json
import re
import uuid
from typing import Any

_TOOL_CALL_BLOCK = re.compile(
    r"<tool_call>\s*(.*?)\s*</tool_call>",
    re.DOTALL | re.IGNORECASE,
)
_FUNCTION_BLOCK = re.compile(
    r"<function=([^>\s]+)>\s*(.*?)\s*</function>",
    re.DOTALL | re.IGNORECASE,
)
_PARAMETER_TAG = re.compile(
    r"<parameter=([^>\s]+)>\s*(.*?)\s*</parameter>",
    re.DOTALL | re.IGNORECASE,
)


def _coerce_param_value(raw: str) -> Any:
    text = raw.strip()
    if not text:
        return ""
    if text.isdigit():
        return int(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _parse_function_block(name: str, body: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for m in _PARAMETER_TAG.finditer(body):
        params[m.group(1).strip()] = _coerce_param_value(m.group(2))
    return {"name": name.strip(), "arguments": params}


def _parse_tool_call_block(block: str) -> dict[str, Any] | None:
    stripped = block.strip()
    if not stripped:
        return None
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        if not isinstance(obj, dict):
            return None
        name = obj.get("name") or obj.get("function")
        if not name:
            return None
        args = obj.get("arguments") or obj.get("parameters") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        return {"name": str(name), "arguments": args}
    fn_match = _FUNCTION_BLOCK.search(stripped)
    if fn_match:
        return _parse_function_block(fn_match.group(1), fn_match.group(2))
    return None


def parse_embedded_tool_calls(content: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract OpenAI-style tool_calls from assistant text (llama.cpp / template output)."""
    if not content or "<tool_call>" not in content.lower():
        return content, []
    calls: list[dict[str, Any]] = []
    remaining = content
    for m in _TOOL_CALL_BLOCK.finditer(content):
        parsed = _parse_tool_call_block(m.group(1))
        if not parsed:
            continue
        calls.append(
            {
                "id": f"call_{uuid.uuid4().hex[:12]}",
                "type": "function",
                "function": {
                    "name": parsed["name"],
                    "arguments": json.dumps(parsed["arguments"]),
                },
            }
        )
        remaining = remaining.replace(m.group(0), "", 1)
    remaining = re.sub(r"\n{3,}", "\n\n", remaining.strip())
    return remaining, calls


def normalize_assistant_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Promote embedded <tool_call> XML in content to message.tool_calls."""
    if msg.get("tool_calls"):
        return msg
    content = msg.get("content")
    if not isinstance(content, str) or "<tool_call>" not in content.lower():
        return msg
    remainder, tool_calls = parse_embedded_tool_calls(content)
    if not tool_calls:
        return msg
    out = dict(msg)
    out["tool_calls"] = tool_calls
    out["content"] = remainder or None
    return out
