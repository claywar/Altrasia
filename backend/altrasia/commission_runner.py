from __future__ import annotations

import json
import logging
from typing import Any

from altrasia.commissions import (
    ISO,
    assignee_at_target,
    sync_presence_statuses,
)
from altrasia.domain.presence import PERSONA_ID, PresenceService

log = logging.getLogger(__name__)


def _commission_id_from_job(job: dict[str, Any]) -> str | None:
    try:
        rationale = json.loads(job.get("selectionRationaleJson") or "{}")
    except json.JSONDecodeError:
        return None
    return rationale.get("commissionId")


def has_active_commission_job(svc: Any, world_id: str, commission_id: str) -> bool:
    for status in ("queued", "running"):
        cur = svc.store.conn.execute(
            """SELECT selectionRationaleJson, trigger FROM GenerationJob
               WHERE worldId = ? AND status = ?""",
            (world_id, status),
        )
        for row in cur.fetchall():
            rationale = row[0]
            try:
                data = json.loads(rationale or "{}")
            except json.JSONDecodeError:
                data = {}
            if data.get("commissionId") == commission_id:
                return True
            if row[1] and str(row[1]).startswith("commission"):
                if data.get("commissionId") == commission_id:
                    return True
    return False


def pause_commissions_during_persona_dialogue(store: Any, world_id: str) -> bool:
    try:
        world = store.get_world(world_id)
        cfg = json.loads((world or {}).get("configJson") or "{}")
    except json.JSONDecodeError:
        cfg = {}
    return bool(cfg.get("pauseCommissionsDuringPersonaDialogue", True))


def persona_dialogue_active_at_scene(svc: Any, world_id: str, scene_id: str) -> bool:
    """Defer commission start while persona is in-scene with active play ([23] §2.3)."""
    if not pause_commissions_during_persona_dialogue(svc.store, world_id):
        return False
    world = svc.store.get_world(world_id)
    if not world or world.get("activeSceneId") != scene_id:
        return False
    scene = svc.store.get_scene(scene_id)
    if not scene:
        return False
    present = PresenceService.parse_present(scene.get("presentJson"))
    if PERSONA_ID not in present:
        return False
    if scene_id in svc.orchestrator._scene_chain_active:
        return True
    if svc.store.list_queued_jobs(world_id):
        for job in svc.store.list_queued_jobs(world_id):
            if job.get("sceneId") == scene_id and job.get("trigger") == "persona_message":
                return True
    msgs = svc.store.list_messages(world_id, scene_id=scene_id)[-8:]
    return any(
        m.get("role") == "user" and not m.get("characterId") for m in msgs[-3:]
    )


async def tick_running_commissions(svc: Any, world_id: str) -> dict[str, Any] | None:
    """Scheduler poll: enqueue commission_tick while status is running ([23] §2.3)."""
    if world_id in svc.paused_worlds:
        return None
    if svc.gpu_queue.busy:
        return None
    if svc.store.list_queued_jobs(world_id):
        return None
    sync_presence_statuses(svc.store, world_id)
    for row in svc.store.list_commissions(world_id):
        if row["status"] != "running":
            continue
        if not assignee_at_target(svc.store, row):
            continue
        if persona_dialogue_active_at_scene(svc, row["worldId"], row["targetSceneId"]):
            continue
        cid = row["commissionId"]
        if has_active_commission_job(svc, world_id, cid):
            continue
        return await enqueue_commission_tick(svc, cid)
    return None


async def tick_commissions(svc: Any, world_id: str) -> dict[str, Any] | None:
    """Try running commission ticks, then start one queued commission (COM-6)."""
    if world_id in svc.paused_worlds:
        return None
    ticked = await tick_running_commissions(svc, world_id)
    if ticked:
        return ticked
    sync_presence_statuses(svc.store, world_id)
    for row in svc.store.list_commissions(world_id):
        if row["status"] != "queued":
            continue
        if not assignee_at_target(svc.store, row):
            continue
        if persona_dialogue_active_at_scene(svc, row["worldId"], row["targetSceneId"]):
            continue
        cid = row["commissionId"]
        if has_active_commission_job(svc, world_id, cid):
            continue
        return await start_commission(svc, cid)
    return None


async def enqueue_commission_tick(svc: Any, commission_id: str) -> dict[str, Any]:
    row = svc.store.get_commission(commission_id)
    if not row:
        raise ValueError("commission not found")
    if row["status"] != "running":
        raise ValueError(f"cannot tick commission in status {row['status']}")
    if not assignee_at_target(svc.store, row):
        raise ValueError("COM-6: assignee not at target scene")
    if persona_dialogue_active_at_scene(svc, row["worldId"], row["targetSceneId"]):
        raise ValueError("persona dialogue active at target scene — commission deferred")
    job = await svc.orchestrator.enqueue_generation(
        world_id=row["worldId"],
        scene_id=row["targetSceneId"],
        character_id=row["assigneeCharacterId"],
        trigger="commission_tick",
        commission_id=commission_id,
    )
    if not job:
        raise RuntimeError("generation not enqueued")
    return {"commissionId": commission_id, "generationJob": job}


async def start_commission(svc: Any, commission_id: str) -> dict[str, Any]:
    row = svc.store.get_commission(commission_id)
    if not row:
        raise ValueError("commission not found")
    if row["status"] not in ("queued", "blocked"):
        raise ValueError(f"cannot start commission in status {row['status']}")
    if not assignee_at_target(svc.store, row):
        svc.store.update_commission(commission_id, status="blocked", updatedAt=ISO())
        raise ValueError("COM-6: assignee not at target scene")
    if persona_dialogue_active_at_scene(svc, row["worldId"], row["targetSceneId"]):
        raise ValueError("persona dialogue active at target scene — commission deferred")
    svc.store.update_commission(commission_id, status="running", updatedAt=ISO())
    job = await svc.orchestrator.enqueue_generation(
        world_id=row["worldId"],
        scene_id=row["targetSceneId"],
        character_id=row["assigneeCharacterId"],
        trigger="commission_started",
        commission_id=commission_id,
    )
    if not job:
        svc.store.update_commission(commission_id, status="queued")
        raise RuntimeError("generation not enqueued")
    return {"commissionId": commission_id, "generationJob": job}
