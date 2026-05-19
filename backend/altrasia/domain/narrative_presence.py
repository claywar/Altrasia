from __future__ import annotations

import re
from typing import Any

from altrasia.domain.presence_ops import presence_join, presence_summon_batch
from altrasia.memory.org_recall import can_summon_others

MAX_SUMMON_PER_LINE = 8

_BRIEFING_HINTS = re.compile(
    r"\b(briefing|brief|meeting|conference|assemble|gather|sync|observe)\b",
    re.I,
)


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


def _names_in_text(text: str, members: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    lower = text.lower()
    for m in members:
        name = m.get("displayName", "")
        if name and name.lower() in lower:
            found.append(m["characterId"])
    return found[:MAX_SUMMON_PER_LINE]


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

    target_scene_id: str | None = None
    m = re.search(
        r"(?:meet\s+(?:me|us)\s+in|gather\s+in|convene\s+in|to)\s+(?:the\s+)?([^.!?\n]{3,60})",
        text,
        re.I,
    )
    if m:
        target_scene_id = _match_scene_by_name(scenes, m.group(1))
    if not target_scene_id:
        m2 = re.search(r"(conference\s+room|main\s+conference)", text, re.I)
        if m2:
            target_scene_id = _match_scene_by_name(scenes, m2.group(0))

    summon_ids = _names_in_text(text, members)
    if not summon_ids and re.search(r"\b(team|directors?|members?|everyone|staff)\b", text, re.I):
        if can_summon_others(cfg, scene_role):
            roster = services.presence.roster(world_id)
            summon_ids = [
                e["characterId"]
                for e in roster.get("elsewhere", []) + roster.get("unplaced", [])
                if e["characterId"] != speaker_id
            ][:MAX_SUMMON_PER_LINE]

    self_move = bool(
        re.search(r"\b(i'll|i will|meet you|heading to|on my way)\b", text, re.I)
        and target_scene_id
    )

    actions: list[dict[str, Any]] = []
    if summon_ids and target_scene_id and can_summon_others(cfg, scene_role):
        actions.append(
            {
                "kind": "summon",
                "targetSceneId": target_scene_id,
                "characterIds": summon_ids,
            }
        )
    elif summon_ids and can_summon_others(cfg, scene_role):
        actions.append(
            {
                "kind": "summon",
                "targetSceneId": scene_id,
                "characterIds": summon_ids,
            }
        )

    if self_move and target_scene_id:
        actions.append({"kind": "join", "sceneId": target_scene_id, "characterId": speaker_id})

    if not actions:
        return None

    return {"mode": mode, "actions": actions}


async def apply_narrative_presence(
    services: Any,
    *,
    world_id: str,
    detection: dict[str, Any],
) -> list[dict[str, Any]]:
    """Apply detected presence actions (auto mode)."""
    if detection.get("mode") != "auto":
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
    return applied
