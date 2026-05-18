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
