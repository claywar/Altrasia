from __future__ import annotations

import json
import re
from typing import Any

from altrasia.domain.presence_ops import presence_join, presence_summon_batch
from altrasia.memory.org_recall import can_summon_others

MAX_SUMMON_PER_LINE = 8

_BRIEFING_HINTS = re.compile(
    r"\b(briefing|brief|meeting|conference|assemble|gather|sync|observe)\b",
    re.I,
)

_PICKUP_HINTS = re.compile(
    r"\b(picks?\s+up|grabs?|takes?|lifts?|snatches?)\b",
    re.I,
)

# Leadership may summon a group only when prose shows deliberate assembly orders.
_AUTHORITY_GATHER_INTENT = re.compile(
    r"\b("
    r"assemble|gather|call\s+(?:in|the)|bring\s+in|pull\s+in|summon|convene|"
    r"meet\s+(?:me|us)\s+in|members?\s+into|directors?\s+into|team\s+into"
    r")\b",
    re.I,
)
_GROUP_SUMMON = re.compile(r"\b(team|directors?|members?|everyone|staff)\b", re.I)


def implies_briefing(text: str) -> bool:
    return bool(_BRIEFING_HINTS.search(text or ""))


def _match_scene_by_name(scenes: list[dict[str, Any]], phrase: str) -> str | None:
    lower = phrase.lower().strip()
    if not lower:
        return None
    for sc in scenes:
        name = (sc.get("locationName") or "").lower()
        sid = sc.get("sceneId", "")
        if lower in name or name in lower:
            return sid
        if lower.replace(" ", "-") in sid.lower():
            return sid
    return None


def _resolve_target_scene(text: str, scenes: list[dict[str, Any]]) -> str | None:
    """Match an explicit destination scene from prose."""
    m = re.search(
        r"(?:meet\s+(?:\w+\s+){0,2}in|gather\s+in|convene\s+in)\s+(?:the\s+)?([^.!?\n]{3,60})",
        text,
        re.I,
    )
    if m:
        sid = _match_scene_by_name(scenes, m.group(1))
        if sid:
            return sid
    m2 = re.search(r"(conference\s+room|main\s+conference)", text, re.I)
    if m2:
        return _match_scene_by_name(scenes, m2.group(0))
    m3 = re.search(
        r"(?:here in|over to|into|join\s+me\s+in)\s+(?:the\s+)?([^.!?\n]{3,50})",
        text,
        re.I,
    )
    if m3:
        return _match_scene_by_name(scenes, m3.group(1))
    return None


def _authority_bulk_summon_ids(
    services: Any,
    *,
    world_id: str,
    speaker_id: str,
    scene_role: str | None,
    cfg: dict[str, Any],
    text: str,
) -> list[str]:
    """Elsewhere/unplaced cast in summonRoles when a leader orders a group assembly."""
    if not can_summon_others(cfg, scene_role):
        return []
    if not _AUTHORITY_GATHER_INTENT.search(text) or not _GROUP_SUMMON.search(text):
        return []
    roles = set(cfg.get("summonRoles") or ["cto", "director"])
    members = {m["characterId"]: m for m in services.store.list_world_characters(world_id)}
    roster = services.presence.roster(world_id)
    ids: list[str] = []
    for entry in roster.get("elsewhere", []) + roster.get("unplaced", []):
        cid = entry["characterId"]
        if cid == speaker_id:
            continue
        role = (members.get(cid) or {}).get("sceneRole")
        if role in roles:
            ids.append(cid)
    return ids[:MAX_SUMMON_PER_LINE]


def _names_in_text(text: str, members: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for m in members:
        name = m.get("displayName", "")
        if name and name.lower() in lower:
            found.append(m["characterId"])
    return found[:MAX_SUMMON_PER_LINE]


def _fixture_keys_in_text(text: str, fixtures: dict[str, Any]) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for key, fixture in fixtures.items():
        label = (fixture.get("label") or key).lower()
        if label in lower or key.lower() in lower:
            found.append(key)
    return found[:3]


def detect_narrative_presence(
    services: Any,
    *,
    world_id: str,
    speaker_id: str,
    scene_id: str,
    output_text: str,
    cfg: dict[str, Any],
) -> dict[str, Any] | None:
    """Heuristic enter/leave/summon from assistant prose (narrative presence auto)."""
    mode = cfg.get("narrativePresenceMode", "off")
    if mode not in ("auto", "detect"):
        return None

    members = services.store.list_world_characters(world_id)
    speaker = next((m for m in members if m["characterId"] == speaker_id), None)
    if not speaker:
        return None
    scene_role = speaker.get("sceneRole")
    scenes = services.store.list_scenes(world_id)
    text = output_text or ""

    target_scene_id = _resolve_target_scene(text, scenes)

    summon_ids = _names_in_text(text, members)
    if not summon_ids and target_scene_id:
        summon_ids = _authority_bulk_summon_ids(
            services,
            world_id=world_id,
            speaker_id=speaker_id,
            scene_role=scene_role,
            cfg=cfg,
            text=text,
        )

    self_move = bool(
        re.search(r"\b(i'll|i will|meet you|heading to|on my way)\b", text, re.I)
        and target_scene_id
    )

    actions: list[dict[str, Any]] = []
    # Summon only when both named people and an explicit destination are stated.
    if summon_ids and target_scene_id and can_summon_others(cfg, scene_role):
        actions.append(
            {
                "kind": "summon",
                "targetSceneId": target_scene_id,
                "characterIds": summon_ids,
            }
        )

    if self_move and target_scene_id:
        actions.append({"kind": "join", "sceneId": target_scene_id, "characterId": speaker_id})

    if _PICKUP_HINTS.search(text):
        scene = services.store.get_scene(scene_id)
        if scene:
            fixtures = json.loads(scene.get("fixturesJson") or "{}")
            for fk in _fixture_keys_in_text(text, fixtures):
                fix = fixtures.get(fk, {})
                if fix.get("kind") in ("discrete", "fixture") and fix.get("portable") is not False:
                    actions.append(
                        {
                            "kind": "pickup",
                            "fixtureKey": fk,
                            "characterId": speaker_id,
                        }
                    )
                    break

    if not actions:
        return None

    return {"mode": mode, "actions": actions}


async def apply_narrative_presence(
    services: Any,
    *,
    world_id: str,
    detection: dict[str, Any],
    speaker_id: str | None = None,
    source_scene_id: str | None = None,
) -> list[dict[str, Any]]:
    """Apply detected presence actions (auto or llm mode)."""
    if detection.get("mode") not in ("auto", "llm"):
        return []
    applied: list[dict[str, Any]] = []
    for act in detection.get("actions") or []:
        if act["kind"] == "summon":
            applied.append(
                await presence_summon_batch(
                    services,
                    world_id=world_id,
                    target_scene_id=act["targetSceneId"],
                    character_ids=act["characterIds"],
                    summoner_id=speaker_id,
                    source_scene_id=source_scene_id,
                    source="narrative",
                    announce=False,
                )
            )
        elif act["kind"] == "join":
            await presence_join(
                services,
                world_id=world_id,
                scene_id=act["sceneId"],
                character_id=act["characterId"],
                action="join",
            )
            applied.append(act)
        elif act["kind"] == "pickup":
            from altrasia.domain.inventory import pickup_fixture
            from altrasia.memory.fixture_sync import sync_scene_fixtures_to_loci

            try:
                out = pickup_fixture(
                    services.store,
                    world_id=world_id,
                    scene_id=source_scene_id or "",
                    character_id=act["characterId"],
                    fixture_key=act["fixtureKey"],
                )
                if source_scene_id:
                    sync_scene_fixtures_to_loci(services.store, scene_id=source_scene_id)
                applied.append({"kind": "pickup", **out})
            except ValueError:
                pass
        elif act["kind"] == "stash_take":
            from altrasia.domain.shared_stash import take_from_stash

            try:
                out = take_from_stash(
                    services.store,
                    world_id=world_id,
                    scene_id=source_scene_id or "",
                    character_id=act["characterId"],
                    stash_key=act["stashKey"],
                    item_id=act.get("itemId"),
                )
                applied.append({"kind": "stash_take", **out})
            except ValueError:
                pass
        elif act["kind"] == "stash_deposit":
            from altrasia.domain.shared_stash import deposit_to_stash

            try:
                out = deposit_to_stash(
                    services.store,
                    world_id=world_id,
                    scene_id=source_scene_id or "",
                    character_id=act["characterId"],
                    stash_key=act["stashKey"],
                    item_id=act["itemId"],
                )
                applied.append({"kind": "stash_deposit", **out})
            except ValueError:
                pass
        elif act["kind"] == "give":
            from altrasia.domain.inventory import give_item

            try:
                out = give_item(
                    services.store,
                    world_id=world_id,
                    from_character_id=act.get("characterId") or speaker_id or "",
                    to_character_id=act["toCharacterId"],
                    item_id=act["itemId"],
                    to_slot=act.get("toSlot", "held"),
                    container_item_id=act.get("containerItemId"),
                )
                applied.append({"kind": "give", **out})
            except ValueError:
                pass
    return applied
