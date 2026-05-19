"""Operator-declared nicknames persisted per world (configJson.operatorAliases)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()
from altrasia.orchestrator.speaker_selection import (
    _chars_for_present_cast,
    _parse_addressed_list,
)

_CONFIG_KEY = "operatorAliases"

_ALIAS_PHRASE = re.compile(
    r"\b(?:"
    r"refer to you as|call you|name you|address you as"
    r"|I\s+will\s+(?:now\s+)?(?:refer to|call)\s+you(?:\s+as)?"
    r"|you(?:'re| are)\s+(?:now\s+)?called"
    r")\s+[\"']?([A-Za-z][\w'-]{1,24})[\"']?",
    re.I,
)


def operator_alias_map(store: Any, world_id: str) -> dict[str, list[str]]:
    """characterId -> lowercase alias tokens."""
    world = store.get_world(world_id)
    if not world:
        return {}
    try:
        cfg = json.loads(world.get("configJson") or "{}")
    except json.JSONDecodeError:
        return {}
    raw = cfg.get(_CONFIG_KEY) or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for cid, names in raw.items():
        if not isinstance(names, list):
            continue
        cleaned = [
            str(n).strip().lower()
            for n in names
            if n and str(n).strip() and len(str(n).strip()) >= 2
        ]
        if cleaned:
            out[str(cid)] = list(dict.fromkeys(cleaned))
    return out


def operator_aliases_for_character(
    store: Any, world_id: str, character_id: str
) -> list[str]:
    world = store.get_world(world_id)
    if not world:
        return []
    try:
        cfg = json.loads(world.get("configJson") or "{}")
    except json.JSONDecodeError:
        return []
    raw = cfg.get(_CONFIG_KEY) or {}
    if not isinstance(raw, dict):
        return []
    names = raw.get(character_id) or []
    if not isinstance(names, list):
        return []
    return [str(n).strip() for n in names if n and str(n).strip()]


def register_operator_alias(
    store: Any, world_id: str, character_id: str, alias: str
) -> bool:
    display = alias.strip()
    token = display.lower()
    if len(token) < 2:
        return False
    world = store.get_world(world_id)
    if not world:
        return False
    try:
        cfg = json.loads(world.get("configJson") or "{}")
    except json.JSONDecodeError:
        cfg = {}
    raw = cfg.get(_CONFIG_KEY)
    if not isinstance(raw, dict):
        raw = {}
    existing = raw.get(character_id)
    if not isinstance(existing, list):
        existing = []
    if token in {str(a).strip().lower() for a in existing}:
        return False
    raw[character_id] = list(dict.fromkeys([*existing, display]))
    cfg[_CONFIG_KEY] = raw
    store.update_world(world_id, configJson=json.dumps(cfg), updatedAt=ISO())
    return True


def parse_operator_alias_declaration(
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
) -> tuple[str, str] | None:
    """
    If the operator names a present character and declares a nickname, return
    (character_id, alias_token).
    """
    match = _ALIAS_PHRASE.search(trigger_text or "")
    if not match:
        return None
    alias = match.group(1).strip()
    if len(alias) < 2:
        return None
    eligible = [c for c in cast if c]
    scene_chars = _chars_for_present_cast(chars, eligible)
    addressees, _, _, _ = _parse_addressed_list(
        trigger_text,
        eligible,
        scene_chars,
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
    )
    if len(addressees) != 1:
        return None
    return addressees[0], alias


def apply_operator_alias_declaration(
    store: Any,
    world_id: str,
    trigger_text: str,
    cast: list[str],
    chars: dict[str, dict],
    *,
    fuzzy_enabled: bool = True,
    fuzzy_max_distance: int = 2,
) -> tuple[str, str] | None:
    """Register nickname when declared; returns (character_id, alias) if new."""
    parsed = parse_operator_alias_declaration(
        trigger_text,
        cast,
        chars,
        fuzzy_enabled=fuzzy_enabled,
        fuzzy_max_distance=fuzzy_max_distance,
    )
    if not parsed:
        return None
    cid, alias = parsed
    if register_operator_alias(store, world_id, cid, alias):
        return cid, alias
    return None
