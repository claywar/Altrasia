from __future__ import annotations

import json
import re
from typing import Any

_tool_snapshots: list[list[str]] = []


def clear_tool_snapshots() -> None:
    _tool_snapshots.clear()


def tool_snapshots() -> list[list[str]]:
    return list(_tool_snapshots)


async def mock_chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    if tools is not None:
        _tool_snapshots.append([t["function"]["name"] for t in tools])
    last_user = ""
    system_text = ""
    for m in messages:
        if m.get("role") == "system":
            system_text += m.get("content", "")
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    lower = last_user.lower()
    if "character authoring assistant" in system_text.lower():
        brief = last_user.strip() or "a mysterious stranger"
        payload = {
            "persona": f"A composed figure shaped by the brief: {brief[:120]}",
            "instructions": "Speak in short, vivid lines. Respect scene presence and memory tools.",
            "focusTags": ["draft"],
            "speechWeight": 0.5,
            "modelProfile": "qwen3.6-35b-a3b",
        }
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(payload),
                    }
                }
            ]
        }
    if tools and "commission errand" in system_text.lower():
        names = [t["function"]["name"] for t in tools]
        has_web_result = any(m.get("role") == "tool" for m in messages)
        if "memory_store" in names and has_web_result:
            key = "commission:mock:summary"
            m = re.search(r'key "([^"]+)"', system_text)
            if m:
                key = m.group(1)
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_mem",
                                    "type": "function",
                                    "function": {
                                        "name": "memory_store",
                                        "arguments": json.dumps(
                                            {
                                                "locusKey": key,
                                                "value": "Mock commission findings from research.",
                                            }
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        if "webtools_invoke" in names:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_web",
                                    "type": "function",
                                    "function": {
                                        "name": "webtools_invoke",
                                        "arguments": json.dumps(
                                            {"query": "commission research context"}
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        if "memory_store" in names:
            key = "commission:mock:summary"
            m = re.search(r'key "([^"]+)"', system_text)
            if m:
                key = m.group(1)
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_mem",
                                    "type": "function",
                                    "function": {
                                        "name": "memory_store",
                                        "arguments": json.dumps(
                                            {
                                                "locusKey": key,
                                                "value": "Mock commission findings from research.",
                                            }
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
    if tools and ("remember" in lower or "capital" in lower):
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "memory_search",
                                    "arguments": json.dumps({"query": "capital"}),
                                },
                            }
                        ],
                    }
                }
            ]
        }
    name = "NPC"
    for m in messages:
        if m.get("role") == "system" and "You are" in m.get("content", ""):
            line = m["content"]
            if "You are " in line:
                name = line.split("You are ", 1)[1].split(".")[0].strip()
                break
    reply = f"*nods* I hear you. ({name} responds in character.)"
    if "whisper" in lower:
        reply = f"*(quietly)* {reply}"
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": reply,
                }
            }
        ]
    }
