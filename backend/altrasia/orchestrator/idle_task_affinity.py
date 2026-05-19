from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_ACTIVE_COMMISSION = frozenset({"queued", "running", "blocked"})


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(ts: str | None) -> float | None:
    dt = _parse_iso(ts)
    if not dt:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds()


def _recency_factor(seconds_ago: float | None, half_life: float) -> float:
    if seconds_ago is None:
        return 0.85
    if half_life <= 0:
        return 1.0
    import math

    return math.exp(-seconds_ago / half_life)


def _task_strength(task: dict[str, Any], *, scene_id: str, half_life: float) -> float:
    sec = _seconds_since(task.get("updatedAt") or task.get("createdAt"))
    recency = _recency_factor(sec, half_life)
    at_scene = 1.2 if task.get("targetSceneId") == scene_id else 1.0
    running = 1.15 if task.get("status") == "running" else 1.0
    return recency * at_scene * running


def collect_active_tasks_by_character(
    services: Any,
    *,
    world_id: str,
    scene_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """Commissions in flight and pending discussion deliverables, keyed by assignee."""
    by_char: dict[str, list[dict[str, Any]]] = defaultdict(list)
    store = services.store

    for row in store.list_commissions(world_id):
        if row.get("status") not in _ACTIVE_COMMISSION:
            continue
        cid = row.get("assigneeCharacterId")
        if not cid:
            continue
        by_char[cid].append(
            {
                "kind": "commission",
                "id": row.get("commissionId"),
                "brief": (row.get("brief") or "").strip()[:240],
                "status": row.get("status"),
                "targetSceneId": row.get("targetSceneId"),
                "updatedAt": row.get("updatedAt") or row.get("createdAt"),
            }
        )

    scene = store.get_scene(scene_id)
    if scene:
        from altrasia.orchestrator.discussion_deliverables import pending_deliverables
        from altrasia.orchestrator.discussion_judgement import get_ensemble_discussion

        activity = get_ensemble_discussion(scene)
        for d in pending_deliverables(activity):
            cid = d.get("characterId")
            if not cid:
                continue
            by_char[cid].append(
                {
                    "kind": "deliverable",
                    "id": d.get("deliverableId"),
                    "brief": (d.get("instruction") or "").strip()[:240],
                    "status": "pending",
                    "targetSceneId": scene_id,
                    "updatedAt": d.get("createdAt") or activity.get("startedAt"),
                }
            )

    return dict(by_char)


def dyad_task_affinity_score(
    a: str,
    b: str,
    tasks_by_char: dict[str, list[dict[str, Any]]],
    *,
    scene_id: str,
    half_life: float,
) -> float:
    """0..1 score: higher when both have recent tasks, especially shared scene/work."""
    ta = tasks_by_char.get(a) or []
    tb = tasks_by_char.get(b) or []
    if not ta and not tb:
        return 0.0

    def best_strength(tasks: list[dict[str, Any]]) -> float:
        if not tasks:
            return 0.0
        return max(_task_strength(t, scene_id=scene_id, half_life=half_life) for t in tasks)

    sa = best_strength(ta)
    sb = best_strength(tb)
    either = max(sa, sb) * 0.45
    both = min(sa, sb) * 0.4 if ta and tb else 0.0
    shared_scene = any(
        t1.get("targetSceneId") and t1.get("targetSceneId") == t2.get("targetSceneId")
        for t1 in ta
        for t2 in tb
    )
    shared_bonus = 0.2 if shared_scene and ta and tb else 0.0
    return min(1.0, either + both + shared_bonus)


def task_hints_for_characters(
    tasks_by_char: dict[str, list[dict[str, Any]]],
    character_ids: list[str],
    *,
    limit_per_char: int = 2,
) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for cid in character_ids:
        for task in (tasks_by_char.get(cid) or [])[:limit_per_char]:
            hints.append({**task, "characterId": cid})
    return hints


def format_task_hints_for_prompt(
    hints: list[dict[str, Any]],
    members: dict[str, dict[str, Any]],
) -> str:
    if not hints:
        return ""
    lines = [
        "Recent in-world tasks for people in this banter (prefer grounding sidebar chat here when natural):"
    ]
    for h in hints[:4]:
        name = (members.get(h.get("characterId") or "") or {}).get(
            "displayName", h.get("characterId", "Someone")
        )
        kind = h.get("kind", "task")
        brief = (h.get("brief") or "").strip()
        if not brief:
            continue
        status = h.get("status") or "active"
        lines.append(f"- {name} ({kind}, {status}): {brief[:180]}")
    return "\n".join(lines) if len(lines) > 1 else ""
