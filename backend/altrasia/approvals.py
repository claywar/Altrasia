from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def world_tool_policy(store: SqlitePersistence, world_id: str) -> dict[str, bool]:
    world = store.get_world(world_id)
    cfg: dict[str, Any] = {}
    if world:
        try:
            cfg = json.loads(world.get("configJson") or "{}")
        except json.JSONDecodeError:
            cfg = {}
    return {
        "requireWebToolApproval": bool(cfg.get("requireWebToolApproval", False)),
        "auditWebTools": bool(cfg.get("auditWebTools", True)),
    }


def create_approval(
    store: SqlitePersistence,
    *,
    world_id: str,
    tool_name: str,
    params: dict[str, Any],
    state: str = "pending",
) -> dict[str, Any]:
    approval_id = str(uuid.uuid4())
    row = {
        "approvalId": approval_id,
        "worldId": world_id,
        "toolName": tool_name,
        "paramsJson": json.dumps(params),
        "state": state,
        "createdAt": ISO(),
    }
    store.insert_approval(row)
    return _serialize(row)


def list_approvals(
    store: SqlitePersistence, world_id: str | None = None, *, state: str | None = "pending"
) -> list[dict[str, Any]]:
    rows = store.list_approvals(world_id=world_id, state=state)
    return [_serialize(r) for r in rows]


def resolve_approval(
    store: SqlitePersistence, approval_id: str, *, approve: bool
) -> dict[str, Any]:
    row = store.get_approval(approval_id)
    if not row:
        raise ValueError("approval not found")
    if row["state"] != "pending":
        raise ValueError(f"approval already {row['state']}")
    new_state = "approved" if approve else "denied"
    store.update_approval(approval_id, state=new_state)
    row = store.get_approval(approval_id)
    return _serialize(row)  # type: ignore[arg-type]


def mark_approval_applied(store: SqlitePersistence, approval_id: str) -> None:
    store.update_approval(approval_id, state="applied")


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    try:
        params = json.loads(row.get("paramsJson") or "{}")
    except json.JSONDecodeError:
        params = {}
    return {
        "approvalId": row["approvalId"],
        "worldId": row["worldId"],
        "toolName": row["toolName"],
        "params": params,
        "state": row["state"],
        "createdAt": row["createdAt"],
    }
