from __future__ import annotations

from typing import Any

from altrasia.domain.presence import PresenceService
from altrasia.persistence.sqlite_store import SqlitePersistence

LEADERSHIP_ROLES = frozenset({"cto", "director", "observer"})


def is_leadership_role(scene_role: str | None) -> bool:
    return bool(scene_role and scene_role in LEADERSHIP_ROLES)


def can_summon_others(cfg: dict[str, Any], scene_role: str | None) -> bool:
    if not cfg.get("castSummonEnabled", True):
        return False
    roles = cfg.get("summonRoles") or ["cto", "director"]
    return bool(scene_role and scene_role in roles)


def build_org_recall(
    store: SqlitePersistence,
    presence: PresenceService,
    *,
    world_id: str,
    character_id: str,
    max_chars: int = 4000,
) -> str:
    """Compact org roster for leadership roles (CTO, directors, observer)."""
    members = store.list_world_characters(world_id)
    speaker = next((m for m in members if m["characterId"] == character_id), None)
    if not speaker or not is_leadership_role(speaker.get("sceneRole")):
        return ""

    roster = presence.roster(world_id)
    loc_by_cid: dict[str, str] = {}
    scene_by_cid: dict[str, str | None] = {}
    for bucket in ("atLocation", "elsewhere", "unplaced"):
        for entry in roster.get(bucket, []):
            cid = entry["characterId"]
            loc_by_cid[cid] = entry.get("locationName") or "(unplaced)"
            scene_by_cid[cid] = entry.get("sceneId")

    lines = ["## Organization roster (world cast)"]
    for m in sorted(members, key=lambda x: (x.get("displayName") or "").lower()):
        cid = m["characterId"]
        if cid == character_id:
            continue
        if m.get("disabled"):
            continue
        role = m.get("sceneRole") or "member"
        loc = loc_by_cid.get(cid, "(unplaced)")
        sid = scene_by_cid.get(cid)
        sid_part = f", sceneId={sid}" if sid else ""
        lines.append(f"- {m['displayName']} ({role}) @ {loc}{sid_part}")

    text = "\n".join(lines)
    return text[:max_chars]
