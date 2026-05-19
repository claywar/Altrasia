from __future__ import annotations

from typing import Any


def scene_messages_for_llm(rows: list[dict[str, Any]], *, limit: int = 12) -> list[dict[str, str]]:
    """Build OpenAI chat turns from scene history.

    Skips empty interrupted generation stubs (failed/cancelled jobs) and merges
    consecutive same-role lines so llama.cpp accepts the payload.
    """
    turns: list[dict[str, str]] = []
    for m in rows[-limit:]:
        if m.get("streamStatus") == "interrupted" and not (m.get("outputText") or "").strip():
            continue
        role = "assistant" if m.get("role") == "assistant" else "user"
        content = (m.get("outputText") or "").strip()
        if not content:
            continue
        turns.append({"role": role, "content": content})
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
