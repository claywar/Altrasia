from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()

_TENSION_KEYWORDS = re.compile(
    r"\b(friction|tension|rivalry|trust|annoyed|grudge|feud|bond|close|allies?|"
    r"conflict|awkward|respect|distrust|betray|forgive)\b",
    re.I,
)


def _parse_social_json(scene: dict[str, Any]) -> dict[str, Any]:
    raw = scene.get("socialStateJson")
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def get_social_state(scene: dict[str, Any]) -> dict[str, Any]:
    return _parse_social_json(scene)


def save_social_state(store: Any, scene_id: str, state: dict[str, Any]) -> None:
    store.update_scene(scene_id, socialStateJson=json.dumps(state), updatedAt=ISO())


def get_variety_ledger(scene: dict[str, Any]) -> list[dict[str, Any]]:
    return list(get_social_state(scene).get("recentBanter") or [])


def append_banter_session(
    store: Any,
    scene_id: str,
    *,
    session_id: str,
    participants: list[str],
    line_count: int,
    window: int,
) -> None:
    scene = store.get_scene(scene_id)
    if not scene:
        return
    state = get_social_state(scene)
    recent = list(state.get("recentBanter") or [])
    recent.append(
        {
            "sessionId": session_id,
            "participants": sorted(participants),
            "endedAt": ISO(),
            "lineCount": line_count,
        }
    )
    state["recentBanter"] = recent[-max(1, window) :]
    save_social_state(store, scene_id, state)


def get_floor_hold(scene: dict[str, Any]) -> dict[str, Any] | None:
    hold = get_social_state(scene).get("floorHold")
    if not isinstance(hold, dict) or not hold.get("active"):
        return None
    return hold


def scene_has_floor_hold(store: Any, scene_id: str) -> bool:
    scene = store.get_scene(scene_id)
    if not scene:
        return False
    hold = get_floor_hold(scene)
    if not hold:
        return False
    claimed_at = hold.get("claimedAt")
    raw_ttl = hold.get("clearAfterSeconds")
    ttl = 90 if raw_ttl is None else int(raw_ttl)
    if ttl <= 0:
        clear_floor_hold(store, scene_id)
        return False
    if claimed_at:
        try:
            dt = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - dt).total_seconds()
            if age >= ttl:
                clear_floor_hold(store, scene_id)
                return False
        except ValueError:
            pass
    return True


def set_floor_hold(
    store: Any,
    scene_id: str,
    *,
    claimed_by: str,
    reason: str,
    source_message_id: str | None = None,
    awaiting_addressees: list[str] | None = None,
    clear_after_seconds: int = 90,
) -> None:
    scene = store.get_scene(scene_id)
    if not scene:
        return
    state = get_social_state(scene)
    state["floorHold"] = {
        "active": True,
        "claimedBy": claimed_by,
        "claimedAt": ISO(),
        "reason": reason,
        "sourceMessageId": source_message_id,
        "awaitingAddressees": list(awaiting_addressees or []),
        "clearAfterSeconds": clear_after_seconds,
    }
    save_social_state(store, scene_id, state)


def clear_floor_hold(store: Any, scene_id: str) -> None:
    scene = store.get_scene(scene_id)
    if not scene:
        return
    state = get_social_state(scene)
    state.pop("floorHold", None)
    save_social_state(store, scene_id, state)


def dyad_key(a: str, b: str) -> str:
    x, y = sorted((a, b))
    return f"{x}|{y}"


def seconds_since_dyad_banter(ledger: list[dict[str, Any]], a: str, b: str) -> float | None:
    key = dyad_key(a, b)
    now = datetime.now(timezone.utc)
    best: float | None = None
    for entry in reversed(ledger):
        parts = entry.get("participants") or []
        if len(parts) < 2:
            continue
        if dyad_key(parts[0], parts[1]) != key:
            continue
        ended = entry.get("endedAt")
        if not ended:
            continue
        try:
            dt = datetime.fromisoformat(ended.replace("Z", "+00:00"))
            sec = (now - dt).total_seconds()
            if best is None or sec < best:
                best = sec
        except ValueError:
            continue
    return best


def relationship_tension_score(memory: Any, speaker_id: str, other_id: str) -> float:
    """Heuristic 0–1 boost from mind locus relationship:{other_id}."""
    if not memory:
        return 0.0
    try:
        rows = memory.store.search_loci(
            "mind", speaker_id, f"relationship:{other_id}", limit=1
        )
        if not rows:
            rows = memory.store.search_loci("mind", speaker_id, other_id, limit=3)
        text = " ".join((r.get("value") or "") for r in rows)
        if not text.strip():
            return 0.0
        hits = len(_TENSION_KEYWORDS.findall(text))
        return min(1.0, 0.35 + hits * 0.15)
    except Exception:
        return 0.0
