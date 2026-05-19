from __future__ import annotations

import re
from typing import Any

from altrasia.orchestrator.single_speaker import operator_trigger_text, trigger_invites_ensemble

_DISCUSSION_CUES = re.compile(
    r"\b(discuss|debate|align on|decide|figure out|work out|resolve|consensus|"
    r"program management|your (?:view|take|perspective)|thoughts on|how (?:do|should) we|"
    r"what (?:do you|should we)|open question|talk through)\b",
    re.I,
)

_RESOLUTION_CUES = re.compile(
    r"\b(we(?:'ve| have) (?:agreed|decided)|agreed to|consensus is|decision is|"
    r"plan is (?:set|clear|to)|next steps are|resolved|solution is|"
    r"to summarize(?: our)? decision|let(?:'s| us) move forward|"
    r"that settles|we have a plan|closing (?:this|the) discussion|"
    r"we(?:'re| are) aligned|settled on|landed on)\b",
    re.I,
)

_STILL_OPEN_CUES = re.compile(
    r"\b(however|but we still|unresolved|disagree|tension|open question|"
    r"need to decide|(?:still )?TBD|not sure yet|what do you think|"
    r"back to you|haven't decided|remains unclear|outstanding)\b",
    re.I,
)


def is_scene_conversation_unresolved(
    store: Any,
    world_id: str,
    scene_id: str,
    *,
    min_cast_replies: int = 2,
    lookback_messages: int = 14,
) -> tuple[bool, str]:
    """Heuristic: group discussion still open (no closure detected in recent cast lines)."""
    rows = store.list_messages(world_id, scene_id=scene_id)[-lookback_messages:]
    op_line = operator_trigger_text(rows)
    cast_lines = [
        (m.get("outputText") or "").strip()
        for m in rows
        if m.get("role") == "assistant"
        and m.get("characterId")
        and (m.get("streamStatus") or "final") == "final"
        and (m.get("outputText") or "").strip()
    ]
    if len(cast_lines) < min_cast_replies:
        return False, "too_few_cast_replies"

    invited = trigger_invites_ensemble(op_line) or bool(_DISCUSSION_CUES.search(op_line))
    question_led = "?" in op_line and bool(_DISCUSSION_CUES.search(op_line))
    if not invited and not question_led:
        return False, "operator_did_not_invite_discussion"

    recent = "\n".join(cast_lines[-8:])
    tail = cast_lines[-1] if cast_lines else ""

    if _RESOLUTION_CUES.search(recent) and not _STILL_OPEN_CUES.search(tail):
        return False, "resolution_detected"

    if _STILL_OPEN_CUES.search(tail):
        return True, "still_open_language"

    if invited or question_led:
        return True, "discussion_invited_no_closure"

    return False, "default_closed"


def effective_continue_depth_limit(
    cfg: dict[str, Any],
    current_depth: int,
    *,
    unresolved: bool,
    addressing_mode: str = "open",
    directed_addressee_count: int = 1,
) -> int:
    """Depth ceiling for the next agent_continue (0-based current_depth)."""
    cap = max(2, int(cfg.get("maxContinueDepthCap", 24)))
    if addressing_mode == "clarification":
        return min(max(0, int(cfg.get("clarificationMaxDepth", 0))), cap)
    if addressing_mode == "directed":
        if directed_addressee_count > 1:
            return min(max(0, directed_addressee_count - 1), cap)
        directed_max = max(0, int(cfg.get("directedReplyMaxDepth", 1)))
        return min(directed_max, cap)
    if addressing_mode == "open" and not unresolved:
        open_cap = max(0, int(cfg.get("openReplyMaxDepth", 2)))
        return min(open_cap, cap)
    base = max(0, int(cfg.get("maxContinueDepth", 2)))
    extended = max(base, int(cfg.get("maxContinueDepthExtended", base + 8)))
    if not cfg.get("continueUntilResolved", True):
        return min(base, cap)
    if current_depth + 1 <= base:
        return min(base, cap)
    if unresolved:
        return min(extended, cap)
    return base
