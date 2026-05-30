from __future__ import annotations

import json
import logging
import re
from typing import Any

log = logging.getLogger(__name__)

_FENCE_RE = re.compile(
    r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
    re.IGNORECASE,
)


def extract_presence_block(text: str) -> tuple[str, dict[str, Any] | None]:
    """NP-LLM-1: strip fenced JSON block from transcript text."""
    if not text:
        return text, None
    match = _FENCE_RE.search(text)
    if not match:
        return text, None
    raw = match.group(1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("narrative presence llm: invalid JSON block")
        return text, None
    if not isinstance(payload, dict):
        return text, None
    presence = payload.get("narrativePresence")
    if not isinstance(presence, dict):
        return text, None
    cleaned = (text[: match.start()] + text[match.end() :]).strip()
    return cleaned, presence


def parse_presence_actions(
    presence: dict[str, Any],
    *,
    speaker_id: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for act in presence.get("actions") or []:
        if not isinstance(act, dict):
            continue
        kind = act.get("kind")
        if not kind:
            continue
        normalized = dict(act)
        if kind in ("join", "pickup", "give", "stash_take", "stash_deposit"):
            normalized.setdefault("characterId", speaker_id)
        actions.append(normalized)
    return actions


def detect_narrative_presence_llm(
    output_text: str,
    *,
    mode: str,
    speaker_id: str,
) -> tuple[str, dict[str, Any] | None]:
    """Parse llm/detect narrative presence from model output."""
    if mode not in ("llm", "detect"):
        return output_text, None
    cleaned, presence = extract_presence_block(output_text)
    if not presence:
        return output_text, None
    actions = parse_presence_actions(presence, speaker_id=speaker_id)
    if not actions:
        return output_text, None
    return cleaned, {"mode": mode, "actions": actions}
