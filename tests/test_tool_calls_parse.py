"""Parse embedded <tool_call> XML from local LLM text output."""

from __future__ import annotations

import json

from altrasia.inference.tool_calls import normalize_assistant_message, parse_embedded_tool_calls


def test_parse_cursor_style_tool_call() -> None:
    content = (
        "<tool_call>\n"
        "<function=memory_search>\n"
        "<parameter=query> password </parameter>\n"
        "<parameter=limit> 5 </parameter>\n"
        "</function>\n"
        "</tool_call>"
    )
    remainder, calls = parse_embedded_tool_calls(content)
    assert remainder == ""
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "memory_search"
    args = json.loads(calls[0]["function"]["arguments"])
    assert args["query"] == "password"
    assert args["limit"] == 5


def test_parse_json_tool_call() -> None:
    payload = {"name": "memory_store", "arguments": {"locusKey": "k", "value": "v"}}
    content = f"<tool_call>{json.dumps(payload)}</tool_call>"
    _, calls = parse_embedded_tool_calls(content)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "memory_store"


def test_normalize_promotes_tool_calls() -> None:
    raw = {
        "role": "assistant",
        "content": (
            "<tool_call><function=memory_search>"
            "<parameter=query>tea</parameter></function></tool_call>"
        ),
    }
    msg = normalize_assistant_message(raw)
    assert msg.get("tool_calls")
    assert msg["tool_calls"][0]["function"]["name"] == "memory_search"
    assert msg.get("content") in ("", None)


def test_normalize_leaves_plain_text() -> None:
    raw = {"role": "assistant", "content": "Hello there."}
    assert normalize_assistant_message(raw) == raw
