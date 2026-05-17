from __future__ import annotations

import json
from typing import Any


async def mock_chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = m.get("content", "")
            break
    lower = last_user.lower()
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
    name = "there"
    for m in messages:
        if m.get("role") == "system" and "You are" in m.get("content", ""):
            line = m["content"]
            if "You are " in line:
                name = line.split("You are ", 1)[1].split(".")[0].strip()
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
