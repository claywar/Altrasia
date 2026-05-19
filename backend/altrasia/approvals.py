from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence
from altrasia.tools.web_access import WEB_TOOL_NAMES

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
    character_id: str | None = None,
    job_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    approval_id = str(uuid.uuid4())
    row = {
        "approvalId": approval_id,
        "worldId": world_id,
        "toolName": tool_name,
        "paramsJson": json.dumps(params),
        "state": state,
        "createdAt": ISO(),
        "characterId": character_id,
        "jobId": job_id,
        "messageId": message_id,
        "resultJson": None,
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


async def execute_web_fetch(services: Any, world_id: str, params: dict[str, Any]) -> dict[str, Any]:
    from altrasia.tools.web_fetch import safe_fetch
    from altrasia.world_config import get_world_config

    query = (params.get("query") or params.get("url") or "").strip()
    wcfg = get_world_config(services.store, world_id)
    use_mock = services.settings.web_tools_mock or wcfg.get("webToolsMock", True)
    if use_mock:
        summary = (
            f"[mock web] No live fetch in dev. Treat as placeholder fact for: {query[:200]}"
            if query
            else "[mock web] supply query or url"
        )
        return {"ok": True, "query": query, "summary": summary, "mock": True}
    url = params.get("url") or (f"https://www.example.org/?q={query}" if query else "")
    return await safe_fetch(url, allowlist=services.settings.web_allowlist_set())


async def apply_web_approval(
    store: SqlitePersistence, services: Any, approval_row: dict[str, Any]
) -> dict[str, Any]:
    try:
        params = json.loads(approval_row.get("paramsJson") or "{}")
    except json.JSONDecodeError:
        params = {}
    result = await execute_web_fetch(services, approval_row["worldId"], params)
    store.update_approval(
        approval_row["approvalId"],
        resultJson=json.dumps(result),
    )
    return result


def is_web_tool(tool_name: str) -> bool:
    return tool_name in WEB_TOOL_NAMES


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    try:
        params = json.loads(row.get("paramsJson") or "{}")
    except json.JSONDecodeError:
        params = {}
    result = None
    raw_result = row.get("resultJson")
    if raw_result:
        try:
            result = json.loads(raw_result)
        except json.JSONDecodeError:
            result = raw_result
    return {
        "approvalId": row["approvalId"],
        "worldId": row["worldId"],
        "toolName": row["toolName"],
        "params": params,
        "state": row["state"],
        "createdAt": row["createdAt"],
        "characterId": row.get("characterId"),
        "jobId": row.get("jobId"),
        "messageId": row.get("messageId"),
        "result": result,
    }
