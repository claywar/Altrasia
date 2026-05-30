from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.presence import PresenceService
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
        "allowedTools": parse_allowed_tools(row) or [],
        "createdAt": row["createdAt"],
        "updatedAt": row["updatedAt"],
    }


def parse_allowed_tools(commission_row: dict[str, Any] | None) -> set[str] | None:
    if not commission_row:
        return None
    raw = commission_row.get("allowedToolsJson")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, list):
        return None
    return {str(x) for x in data if x}


def create_commission(
    store: SqlitePersistence,
    world_id: str,
    *,
    assignee_character_id: str,
    target_scene_id: str,
    brief: str,
    deliverable_policy: str = "mind",
    allowed_tools: list[str] | None = None,
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
            "allowedToolsJson": json.dumps(allowed_tools) if allowed_tools else None,
            "forceCompleteReason": None,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return _serialize(store.get_commission(commission_id))  # type: ignore[arg-type]


def list_commissions(store: SqlitePersistence, world_id: str) -> list[dict[str, Any]]:
    return [_serialize(r) for r in store.list_commissions(world_id)]


def assignee_at_target(
    store: SqlitePersistence, commission_row: dict[str, Any]
) -> bool:
    """COM-6: assignee must be present at targetSceneId."""
    scene = store.get_scene(commission_row["targetSceneId"])
    if not scene:
        return False
    present = PresenceService.parse_present(scene.get("presentJson"))
    return commission_row["assigneeCharacterId"] in present


def sync_presence_statuses(
    store: SqlitePersistence, world_id: str
) -> list[str]:
    """Update queued/blocked from presence; returns commissionIds that changed."""
    changed: list[str] = []
    for row in store.list_commissions(world_id):
        status = row["status"]
        if status in ("done", "failed"):
            continue
        at_target = assignee_at_target(store, row)
        cid = row["commissionId"]
        if status == "running":
            if not at_target:
                store.update_commission(cid, status="blocked", updatedAt=ISO())
                changed.append(cid)
            continue
        if at_target and status == "blocked":
            store.update_commission(cid, status="queued", updatedAt=ISO())
            changed.append(cid)
        elif not at_target and status == "queued":
            store.update_commission(cid, status="blocked", updatedAt=ISO())
            changed.append(cid)
    return changed


def deliverable_summary_key(commission_row: dict[str, Any]) -> str:
    prefix = commission_row.get("deliverableLocusPrefix") or ""
    return f"{prefix}summary"


def commission_deliverable_keys(
    store: SqlitePersistence,
    memory: Any,
    commission_row: dict[str, Any],
) -> list[str]:
    """Collect all deliverable locus keys after mind store exists (COM-3/4)."""
    keys = [deliverable_summary_key(commission_row)]
    policy = commission_row.get("deliverablePolicy") or "mind"
    if policy not in ("world_pool_at_target", "both"):
        return keys
    mind_key = keys[0]
    row = store.conn.execute(
        "SELECT value FROM Locus WHERE pool = 'mind' AND ownerId = ? AND locusKey = ?",
        (commission_row["assigneeCharacterId"], mind_key),
    ).fetchone()
    if not row:
        return keys
    world_key = f"{commission_row.get('deliverableLocusPrefix', '')}board"
    memory.memory_store(
        pool="world",
        owner_id=commission_row["targetSceneId"],
        locus_key=world_key,
        value=row[0][:8000],
    )
    keys.append(world_key)
    return keys


def mind_deliverable_exists(store: SqlitePersistence, commission_row: dict[str, Any]) -> bool:
    """COM-2: assignee mind pool has the commission summary locus."""
    key = deliverable_summary_key(commission_row)
    row = store.conn.execute(
        "SELECT 1 FROM Locus WHERE pool = 'mind' AND ownerId = ? AND locusKey = ?",
        (commission_row["assigneeCharacterId"], key),
    ).fetchone()
    return row is not None


def complete_commission_with_output(
    store: SqlitePersistence,
    memory: Any,
    commission_id: str,
    output_text: str,
) -> dict[str, Any]:
    """COM-2/3/4: persist deliverables per policy and mark done."""
    row = store.get_commission(commission_id)
    if not row:
        raise ValueError("commission not found")
    policy = row.get("deliverablePolicy") or "mind"
    key = deliverable_summary_key(row)
    cleaned = (output_text or "").strip()
    if not cleaned:
        raise ValueError("empty commission output")
    keys: list[str] = []
    memory.memory_store(
        pool="mind",
        owner_id=row["assigneeCharacterId"],
        locus_key=key,
        value=cleaned[:8000],
        overwrite=True,
    )
    keys.append(key)
    from altrasia.evidence import record_evidence

    record_evidence(
        store,
        locus_key=key,
        pool="mind",
        owner_id=row["assigneeCharacterId"],
        source_kind="commission",
        source_ref=commission_id,
        commission_id=commission_id,
    )
    if policy in ("world_pool_at_target", "both"):
        world_key = f"{row.get('deliverableLocusPrefix', '')}board"
        memory.memory_store(
            pool="world",
            owner_id=row["targetSceneId"],
            locus_key=world_key,
            value=cleaned[:8000],
            overwrite=True,
        )
        keys.append(world_key)
    return patch_commission(
        store,
        commission_id,
        status="done",
        deliverable_locus_keys=keys,
    )


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
