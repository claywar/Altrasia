from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()

VALID_STATUS = frozenset({"queued", "running", "blocked", "done", "failed"})
VALID_POLICY = frozenset({"mind", "world_pool_at_target", "both"})


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    keys = row.get("deliverableLocusKeysJson")
    try:
        locus_keys = json.loads(keys) if keys else []
    except json.JSONDecodeError:
        locus_keys = []
    return {
        "commissionId": row["commissionId"],
        "worldId": row["worldId"],
        "assigneeCharacterId": row["assigneeCharacterId"],
        "targetSceneId": row["targetSceneId"],
        "brief": row["brief"],
        "status": row["status"],
        "deliverablePolicy": row["deliverablePolicy"],
        "deliverableLocusPrefix": row.get("deliverableLocusPrefix"),
        "deliverableLocusKeys": locus_keys,
        "forceCompleteReason": row.get("forceCompleteReason"),
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }


def create_commission(
    store: SqlitePersistence,
    world_id: str,
    *,
    assignee_character_id: str,
    target_scene_id: str,
    brief: str,
    deliverable_policy: str = "mind",
) -> dict[str, Any]:
    """COM-1: default deliverable policy is mind."""
    if deliverable_policy not in VALID_POLICY:
        raise ValueError(f"invalid deliverablePolicy: {deliverable_policy}")
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    scene = store.get_scene(target_scene_id)
    if not scene or scene["worldId"] != world_id:
        raise ValueError("targetSceneId not in world")
    chars = {c["characterId"] for c in store.list_world_characters(world_id)}
    if assignee_character_id not in chars:
        raise ValueError("assignee not in world cast")
    commission_id = str(uuid.uuid4())
    prefix = f"commission:{commission_id}:"
    now = ISO()
    store.insert_commission(
        {
            "commissionId": commission_id,
            "worldId": world_id,
            "assigneeCharacterId": assignee_character_id,
            "targetSceneId": target_scene_id,
            "brief": brief,
            "status": "queued",
            "deliverablePolicy": deliverable_policy,
            "deliverableLocusPrefix": prefix,
            "deliverableLocusKeysJson": "[]",
            "allowedToolsJson": None,
            "forceCompleteReason": None,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return _serialize(store.get_commission(commission_id))  # type: ignore[arg-type]


def list_commissions(store: SqlitePersistence, world_id: str) -> list[dict[str, Any]]:
    return [_serialize(r) for r in store.list_commissions(world_id)]


def patch_commission(
    store: SqlitePersistence,
    commission_id: str,
    *,
    status: str | None = None,
    deliverable_locus_keys: list[str] | None = None,
    force_complete_reason: str | None = None,
) -> dict[str, Any]:
    row = store.get_commission(commission_id)
    if not row:
        raise ValueError("commission not found")
    fields: dict[str, Any] = {"updatedAt": ISO()}
    if status is not None:
        if status not in VALID_STATUS:
            raise ValueError(f"invalid status: {status}")
        if status == "done":
            keys = deliverable_locus_keys
            if keys is None:
                try:
                    keys = json.loads(row.get("deliverableLocusKeysJson") or "[]")
                except json.JSONDecodeError:
                    keys = []
            reason = force_complete_reason or row.get("forceCompleteReason")
            if not keys and not reason:
                raise ValueError(
                    "COM-2: done requires deliverableLocusKeys or forceCompleteReason"
                )
            if reason:
                fields["forceCompleteReason"] = reason
        fields["status"] = status
    if deliverable_locus_keys is not None:
        fields["deliverableLocusKeysJson"] = json.dumps(deliverable_locus_keys)
    if force_complete_reason is not None and status != "done":
        fields["forceCompleteReason"] = force_complete_reason
    store.update_commission(commission_id, **fields)
    return _serialize(store.get_commission(commission_id))  # type: ignore[arg-type]
