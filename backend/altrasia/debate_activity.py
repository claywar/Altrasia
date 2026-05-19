from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()

DEBATE_PHASES = ("opening", "cross", "rebuttal", "closing", "synthesis")


def parse_activity(scene: dict[str, Any]) -> dict[str, Any] | None:
    raw = scene.get("activityJson")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if data.get("kind") not in ("debate", "conversation", "banter"):
        return None
    return data


def activity_current_speaker(activity: dict[str, Any]) -> str | None:
    """DEB-2 / AO-22: ordered speaker for debate, conversation, or banter."""
    return debate_current_speaker(activity)


def debate_current_speaker(activity: dict[str, Any]) -> str | None:
    order = activity.get("speakingOrder") or []
    if not order:
        return None
    idx = int(activity.get("currentIndex") or 0)
    if idx < 0 or idx >= len(order):
        return None
    return order[idx]


def start_debate(
    store: SqlitePersistence,
    scene_id: str,
    *,
    speaking_order: list[str],
    phase: str = "opening",
) -> dict[str, Any]:
    if phase not in DEBATE_PHASES:
        raise ValueError(f"invalid debate phase: {phase}")
    if len(speaking_order) < 1:
        raise ValueError("speakingOrder required")
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    present = json.loads(scene.get("presentJson") or "[]")
    for cid in speaking_order:
        if cid not in present:
            raise ValueError(f"speaker {cid} not present at scene")
    activity = {
        "kind": "debate",
        "phase": phase,
        "speakingOrder": speaking_order,
        "currentIndex": 0,
        "debateDeliverablePolicy": "mind_per_participant",
    }
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def clear_debate(store: SqlitePersistence, scene_id: str) -> None:
    store.update_scene(scene_id, activityJson=None, updatedAt=ISO())


def advance_debate_speaker(store: SqlitePersistence, scene_id: str) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    activity = parse_activity(scene)
    if not activity:
        raise ValueError("no debate activity on scene")
    order = activity["speakingOrder"]
    idx = int(activity.get("currentIndex") or 0) + 1
    if idx >= len(order):
        idx = 0
    activity["currentIndex"] = idx
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def advance_debate_phase(store: SqlitePersistence, scene_id: str) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    activity = parse_activity(scene)
    if not activity:
        raise ValueError("no debate activity on scene")
    phase = activity.get("phase", "opening")
    try:
        nxt = DEBATE_PHASES[DEBATE_PHASES.index(phase) + 1]
    except (ValueError, IndexError):
        nxt = "synthesis"
    activity["phase"] = nxt
    activity["currentIndex"] = 0
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def get_active_banter(scene: dict[str, Any]) -> dict[str, Any] | None:
    activity = parse_activity(scene)
    if activity and activity.get("kind") == "banter":
        return activity
    return None


def start_banter(
    store: SqlitePersistence,
    scene_id: str,
    *,
    speaking_order: list[str],
    session_id: str,
    turns_remaining: int = 3,
) -> dict[str, Any]:
    if len(speaking_order) < 2:
        raise ValueError("banter requires two speakers")
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    present = json.loads(scene.get("presentJson") or "[]")
    for cid in speaking_order:
        if cid not in present:
            raise ValueError(f"speaker {cid} not present at scene")
    activity = {
        "kind": "banter",
        "speakingOrder": list(speaking_order),
        "participants": sorted(set(speaking_order)),
        "currentIndex": 0,
        "sessionId": session_id,
        "turnsRemaining": turns_remaining,
        "lineCount": 0,
        "startedAt": ISO(),
    }
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def clear_banter(store: SqlitePersistence, scene_id: str) -> None:
    scene = store.get_scene(scene_id)
    if not scene:
        return
    activity = parse_activity(scene)
    if activity and activity.get("kind") == "banter":
        store.update_scene(scene_id, activityJson=None, updatedAt=ISO())


def advance_banter_turn(store: SqlitePersistence, scene_id: str) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    activity = get_active_banter(scene)
    if not activity:
        raise ValueError("no banter activity on scene")
    activity["lineCount"] = int(activity.get("lineCount") or 0) + 1
    activity["turnsRemaining"] = max(0, int(activity.get("turnsRemaining") or 0) - 1)
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def banter_exhausted(activity: dict[str, Any]) -> bool:
    return int(activity.get("turnsRemaining") or 0) <= 0


def set_banter_current_speaker(
    store: SqlitePersistence, scene_id: str, character_id: str
) -> dict[str, Any] | None:
    scene = store.get_scene(scene_id)
    if not scene:
        return None
    activity = get_active_banter(scene)
    if not activity:
        return None
    order = activity.get("speakingOrder") or []
    if character_id in order:
        activity["currentIndex"] = order.index(character_id)
    store.update_scene(scene_id, activityJson=json.dumps(activity), updatedAt=ISO())
    return activity


def topic_exhausted_recent_lines(texts: list[str]) -> bool:
    """Cheap overlap heuristic for last two banter lines."""
    if len(texts) < 2:
        return False
    a, b = texts[-2].lower().split(), texts[-1].lower().split()
    if not a or not b:
        return False
    sa, sb = set(a), set(b)
    overlap = len(sa & sb) / max(1, min(len(sa), len(sb)))
    return overlap > 0.72


def finalize_debate_synthesis(
    memory: Any, scene_id: str, activity: dict[str, Any], synthesis_text: str
) -> list[str]:
    """DEB-1: mind loci per participant under debate:{sceneId}:summary."""
    keys: list[str] = []
    prefix = f"debate:{scene_id}:"
    cleaned = (synthesis_text or "").strip()
    if not cleaned:
        return keys
    for cid in activity.get("speakingOrder") or []:
        key = f"{prefix}{cid}:summary"
        memory.memory_store(pool="mind", owner_id=cid, locus_key=key, value=cleaned[:4000])
        keys.append(key)
    return keys
