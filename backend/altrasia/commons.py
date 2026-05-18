from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def commons_locus_key(world_id: str, key: str) -> str:
    return f"world:{world_id}:commons:{key}"


def list_commons(store: SqlitePersistence, world_id: str) -> list[dict[str, str]]:
    rows = store.conn.execute(
        """SELECT locusKey, value, updatedAt FROM Locus
           WHERE pool = 'commons' AND ownerId = ? ORDER BY locusKey""",
        (world_id,),
    ).fetchall()
    out: list[dict[str, str]] = []
    prefix = f"world:{world_id}:commons:"
    for row in rows:
        key = row[0]
        short = key[len(prefix) :] if key.startswith(prefix) else key
        out.append({"key": short, "locusKey": key, "value": row[1], "updatedAt": row[2]})
    return out


def set_commons(
    memory: Any,
    store: SqlitePersistence,
    world_id: str,
    *,
    key: str,
    text: str,
) -> dict[str, str]:
    cleaned = (key or "").strip()
    if not cleaned:
        raise ValueError("commons key required")
    body = (text or "").strip()
    if not body:
        raise ValueError("commons text required")
    locus = commons_locus_key(world_id, cleaned)
    memory.memory_store(pool="commons", owner_id=world_id, locus_key=locus, value=body[:8000])
    return {"key": cleaned, "locusKey": locus, "worldId": world_id}


def character_has_commons_access(cfg: dict[str, Any], character_id: str) -> bool:
    access = cfg.get("commonsAccessIds")
    if not access:
        return False
    if isinstance(access, list):
        return character_id in access
    if isinstance(access, dict):
        return bool(access.get(character_id))
    return False
