from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
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
    state["lastBanterEndedAt"] = ISO()
    save_social_state(store, scene_id, state)


def seconds_since_last_banter(scene: dict[str, Any]) -> float | None:
    """Seconds since any banter session ended at this scene."""
    state = get_social_state(scene)
    ended = state.get("lastBanterEndedAt")
    if ended:
        try:
            dt = datetime.fromisoformat(str(ended).replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).total_seconds()
        except ValueError:
            pass
    ledger = get_variety_ledger(scene)
    if not ledger:
        return None
    now = datetime.now(timezone.utc)
    best: float | None = None
    for entry in reversed(ledger):
        ts = entry.get("endedAt")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            sec = (now - dt).total_seconds()
            if best is None or sec < best:
                best = sec
        except ValueError:
            continue
    return best


def extend_digest_window(
    store: Any,
    scene_id: str,
    *,
    seconds: int,
) -> None:
    """Pause new banter starts so cast can digest operator-influenced work."""
    if seconds <= 0:
        return
    scene = store.get_scene(scene_id)
    if not scene:
        return
    state = get_social_state(scene)
    now = datetime.now(timezone.utc)
    until = now + timedelta(seconds=seconds)
    state["digestUntil"] = until.isoformat()
    save_social_state(store, scene_id, state)


def _digest_until_active(scene: dict[str, Any]) -> bool:
    state = get_social_state(scene)
    raw = state.get("digestUntil")
    if not raw:
        return False
    try:
        until = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if datetime.now(timezone.utc) >= until:
            return False
        return True
    except ValueError:
        return False


def scene_has_recent_operator_activity(
    store: Any,
    world_id: str,
    scene_id: str,
    *,
    window_seconds: float,
    message_limit: int = 8,
) -> bool:
    if window_seconds <= 0:
        return False
    now = datetime.now(timezone.utc)
    msgs = store.list_messages(world_id, scene_id=scene_id)[-message_limit:]
    for m in reversed(msgs):
        if m.get("characterId"):
            continue
        if m.get("role") != "user":
            continue
        created = m.get("createdAt")
        if not created:
            return True
        try:
            dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            if (now - dt).total_seconds() <= window_seconds:
                return True
        except ValueError:
            return True
    return False


def scene_operator_quiet_active(
    svc: Any,
    world_id: str,
    scene_id: str,
) -> bool:
    """True while operator dialogue should block ambient idle/banter (single-GPU courtesy)."""
    from altrasia.world_config import get_idle_social_config

    cfg = get_idle_social_config(svc.store, world_id)
    cooldown = float(cfg.get("operatorInteractionCooldownSeconds", 120))
    if cooldown <= 0:
        return False
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return False
    if _digest_until_active(scene):
        return True
    return scene_has_recent_operator_activity(
        svc.store,
        world_id,
        scene_id,
        window_seconds=cooldown,
    )


def scene_digest_window_active(
    svc: Any,
    world_id: str,
    scene_id: str,
    *,
    window_seconds: float,
) -> bool:
    """True when operator-influenced work should block new banter starts."""
    if window_seconds <= 0:
        return False
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return False
    if _digest_until_active(scene):
        return True
    if scene_has_recent_operator_activity(
        svc.store,
        world_id,
        scene_id,
        window_seconds=window_seconds,
    ):
        return True
    from altrasia.domain.presence import PERSONA_ID
    from altrasia.orchestrator.idle_task_affinity import collect_active_tasks_by_character

    present = [
        c
        for c in json.loads(scene.get("presentJson") or "[]")
        if c not in (PERSONA_ID,)
    ]
    if not present:
        return False
    by_char = collect_active_tasks_by_character(
        svc, world_id=world_id, scene_id=scene_id
    )
    for cid in present:
        tasks = by_char.get(cid) or []
        for task in tasks:
            if task.get("targetSceneId") == scene_id:
                return True
    return False


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
