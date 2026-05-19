from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_MAP_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "map-layouts"
_JUDGE_MARKER = "discussion sufficiency judge"

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
    if "map layout assistant" in system_text.lower():
        scope = "mini"
        for line in last_user.splitlines():
            if line.startswith("Scope:"):
                scope = line.split(":", 1)[1].strip().lower() or "mini"
        if scope == "unified":
            scope = "site"
        fixture = _MAP_FIXTURES / f"{scope}-valid.json"
        if not fixture.is_file():
            fixture = _MAP_FIXTURES / "mini-valid.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        payload["schemaVersion"] = 2
        return {
            "choices": [{"message": {"role": "assistant", "content": json.dumps(payload)}}]
        }
    if "world bootstrap assistant" in system_text.lower():
        payload = {
            "schemaVersion": 2,
            "newScenes": [
                {
                    "tempId": "scene-garden",
                    "locationName": "Garden",
                    "locationDescription": "A rooftop terrace off the lobby.",
                    "connectFromSceneId": None,
                    "exitLabel": "Garden path",
                }
            ],
            "layout": {
                "schemaVersion": 2,
                "scope": "mini",
                "scenes": [
                    {
                        "sceneId": "scene-garden",
                        "mapPosition": {"x": 70, "y": 60},
                        "position3d": {"x": 0.4, "y": 0.2, "z": 0},
                    }
                ],
            },
        }
        return {
            "choices": [{"message": {"role": "assistant", "content": json.dumps(payload)}}]
        }
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
    if _JUDGE_MARKER in system_text.lower():
        insufficient = "not sufficient" in last_user.lower() or "gaps" in last_user.lower()
        if "tbd" in last_user.lower() or "tension" in last_user.lower():
            insufficient = True
        payload = {
            "sufficient": not insufficient,
            "reason": "mock_judgement_insufficient" if insufficient else "mock_judgement_sufficient",
            "outstandingGaps": ["dependencies", "owners"] if insufficient else [],
            "influencedByCharacters": "discussion_signal" in last_user.lower(),
        }
        return {
            "choices": [
                {"message": {"role": "assistant", "content": json.dumps(payload)}}
            ]
        }
    if tools and "commission errand" in system_text.lower():
        names = [t["function"]["name"] for t in tools]
        tool_rounds = sum(1 for m in messages if m.get("role") == "tool")
        needs_web = "webtools_invoke" in names

        def _plain_done() -> dict[str, Any]:
            return {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Commission complete. Findings stored in mind.",
                        }
                    }
                ]
            }

        if needs_web and tool_rounds >= 2:
            return _plain_done()
        if not needs_web and tool_rounds >= 1:
            return _plain_done()

        def _memory_store_response() -> dict[str, Any]:
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

        if needs_web and tool_rounds == 0:
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
            return _memory_store_response()
    if tools and "commission errand" not in system_text.lower():
        names = [t["function"]["name"] for t in tools]
        tool_rounds = sum(1 for m in messages if m.get("role") == "tool")
        briefing_line = any(
            k in lower
            for k in (
                "conference room",
                "briefing",
                "assemble",
                "gather",
                "members into",
                "call the members",
            )
        )
        if briefing_line:
            summon_done = any(
                tc.get("function", {}).get("name") == "scene_summon"
                for m in messages
                if m.get("role") == "assistant"
                for tc in (m.get("tool_calls") or [])
            )
            memory_only = not any(n.startswith("scene_") for n in names)
            if tool_rounds == 0 and memory_only and "memory_search" in names:
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_mem_brief",
                                        "type": "function",
                                        "function": {
                                            "name": "memory_search",
                                            "arguments": json.dumps({"query": "team directors"}),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            if not summon_done and (not memory_only or "scene_summon" in names):
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_summon",
                                        "type": "function",
                                        "function": {
                                            "name": "scene_summon",
                                            "arguments": json.dumps(
                                                {
                                                    "targetSceneId": "scene-conference-room",
                                                    "characterIds": [
                                                        "char-sofia-mendez",
                                                        "char-liam-park",
                                                    ],
                                                }
                                            ),
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                }
            if summon_done:
                return {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": (
                                    "Understood. I've asked Sofia Mendez and Liam Park to meet "
                                    "us in the main conference room for the briefing."
                                ),
                            }
                        }
                    ]
                }
        if re.search(r"\bremember\b", lower) or re.search(r"\bcapital\b", lower):
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
