from __future__ import annotations

import json
from typing import Any

from altrasia.perception.scope import can_perceive


_SCENE_PREFIX = "[Scene] "


def _is_presence_announce(message: dict[str, Any]) -> bool:
    try:
        meta = json.loads(message.get("metaJson") or "{}")
    except (json.JSONDecodeError, TypeError):
        return False
    return (meta.get("orchestration") or {}).get("kind") == "presence_announce"


def thinking_safe_chat_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rewrite prior assistant *content* turns so enable_thinking servers accept the payload.

    Tool-call-only assistant messages (content empty, tool_calls set) are left intact.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "system":
            out.append(m)
            continue
        if role == "assistant":
            content = (m.get("content") or "").strip()
            if content:
                if content.startswith(_SCENE_PREFIX):
                    out.append({"role": "user", "content": content})
                else:
                    out.append({"role": "user", "content": f"{_SCENE_PREFIX}{content}"})
                continue
            out.append(m)
            continue
        out.append(m)
    return out


def scene_messages_for_llm(
    rows: list[dict[str, Any]],
    *,
    limit: int = 12,
    viewer_id: str | None = None,
    present: list[str] | None = None,
    viewer_scene_id: str | None = None,
) -> list[dict[str, str]]:
    """Build OpenAI chat turns from scene history.

    Skips empty interrupted generation stubs. Prior cast lines are sent as user
    ``[Scene] …`` context (thinking-safe for llama.cpp enable_thinking); persona
    lines stay user without the prefix.
    """
    turns: list[dict[str, str]] = []
    present_list = present or []
    for m in rows[-limit:]:
        if _is_presence_announce(m):
            continue
        if viewer_id and present is not None:
            if not can_perceive(
                viewer_id=viewer_id,
                message=m,
                present=present_list,
                viewer_scene_id=viewer_scene_id,
            ):
                continue
        if m.get("streamStatus") == "interrupted" and not (m.get("outputText") or "").strip():
            continue
        content = (m.get("outputText") or "").strip()
        if not content:
            continue
        if m.get("role") == "assistant":
            turns.append({"role": "user", "content": f"{_SCENE_PREFIX}{content}"})
        else:
            turns.append({"role": "user", "content": content})
    return _collapse_trailing_same_role(turns, "assistant")


def _collapse_trailing_same_role(
    turns: list[dict[str, str]], role: str
) -> list[dict[str, str]]:
    if len(turns) < 2:
        return turns
    start = len(turns) - 1
    while start >= 0 and turns[start]["role"] == role:
        start -= 1
    run_len = len(turns) - (start + 1)
    if run_len < 2:
        return turns
    merged = "\n\n".join(t["content"] for t in turns[start + 1 :])
    return turns[: start + 1] + [{"role": role, "content": merged}]
