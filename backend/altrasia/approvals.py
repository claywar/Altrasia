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


def effective_web_allowlist(services: Any, world_id: str) -> set[str]:
    from altrasia.world_config import get_world_config

    hosts = set(services.settings.web_allowlist_set())
    cfg = get_world_config(services.store, world_id)
    extra = cfg.get("webAllowlistHosts") or cfg.get("webAllowlist")
    if isinstance(extra, str):
        hosts |= {h.strip().lower() for h in extra.split(",") if h.strip()}
    elif isinstance(extra, list):
        hosts |= {str(h).strip().lower() for h in extra if str(h).strip()}
    return hosts


def resolve_fetch_url(params: dict[str, Any]) -> str | None:
    """Build https URL from tool params; never silently substitute example.com."""
    url = str(params.get("url") or "").strip()
    query = str(params.get("query") or "").strip()
    if url:
        if "://" not in url:
            return f"https://{url.lstrip('/')}"
        return url
    if query and " " not in query and "." in query.split("/")[0]:
        q = query if query.startswith("http") else f"https://{query.lstrip('/')}"
        return q
    return None


def web_approval_summary_for_prompt(result: dict[str, Any]) -> str:
    """Text injected into the post-approval generation system prompt."""
    if result.get("mock"):
        return (
            "[Development stub — not a live page fetch.]\n"
            f"{result.get('summary', '')}\n"
            "Tell the operator clearly that this is a dev placeholder, not real site content."
        )
    if not result.get("ok"):
        err = result.get("error") or "fetch failed"
        return (
            f"Web fetch failed: {err}\n"
            "Report this failure to the operator. Do not invent headlines or claim the fetch succeeded."
        )
    return str(result.get("summary") or result.get("text") or "")[:4000]


async def execute_web_fetch(services: Any, world_id: str, params: dict[str, Any]) -> dict[str, Any]:
    from altrasia.tools.web_fetch import safe_fetch
    from altrasia.world_config import get_world_config

    query = (params.get("query") or params.get("url") or "").strip()
    wcfg = get_world_config(services.store, world_id)
    use_mock = services.settings.web_tools_mock or bool(wcfg.get("webToolsMock"))
    if use_mock:
        summary = (
            f"[mock web] No live fetch in dev. Treat as placeholder fact for: {query[:200]}"
            if query
            else "[mock web] supply query or url"
        )
        return {"ok": True, "query": query, "summary": summary, "mock": True}
    url = resolve_fetch_url(params)
    if not url:
        return {
            "ok": False,
            "error": "live fetch requires a url (or a single hostname); query-only search is not supported",
        }
    return await safe_fetch(url, allowlist=effective_web_allowlist(services, world_id))


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
