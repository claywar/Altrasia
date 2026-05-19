from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

ISO = lambda: datetime.now(timezone.utc).isoformat()

AnnouncePerspective = Literal["source", "target", "operator"]
AnnounceSource = Literal["tool", "narrative", "operator"]


def _display_names(store: Any, world_id: str, character_ids: list[str]) -> list[str]:
    members = {m["characterId"]: m for m in store.list_world_characters(world_id)}
    names: list[str] = []
    for cid in character_ids:
        names.append((members.get(cid) or {}).get("displayName") or cid)
    return names


def _name_list(names: list[str]) -> str:
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def format_summon_announcement(
    summoner_name: str | None,
    summoned_names: list[str],
    target_location: str,
    *,
    perspective: AnnouncePerspective,
) -> str:
    """Build chronicle text for a summon assistance line."""
    called = _name_list(summoned_names)
    if not called:
        return ""

    if perspective == "operator" or not summoner_name:
        return f"{called} {'was' if len(summoned_names) == 1 else 'were'} called to {target_location}."

    if perspective == "source":
        return f"{summoner_name} requested assistance from {called}."

    return f"{summoner_name} asked {called} to join {target_location}."


def _build_meta(
    *,
    summoner_id: str | None,
    summoned_ids: list[str],
    target_scene_id: str,
    source: AnnounceSource,
    related_message_id: str | None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "communication": {"scope": "presence"},
        "presence": {
            "action": "summon",
            "summonedIds": summoned_ids,
            "targetSceneId": target_scene_id,
            "source": source,
        },
        "orchestration": {"kind": "presence_announce"},
    }
    if summoner_id:
        meta["presence"]["summonerId"] = summoner_id
    if related_message_id:
        meta["orchestration"]["relatedMessageId"] = related_message_id
    return meta


async def announce_summon(
    services: Any,
    *,
    world_id: str,
    target_scene_id: str,
    summoned_ids: list[str],
    summoner_id: str | None = None,
    source_scene_id: str | None = None,
    source: AnnounceSource = "tool",
    related_message_id: str | None = None,
) -> None:
    """Insert presence-scope chronicle lines after a successful summon."""
    from altrasia.world_config import get_world_config

    cfg = get_world_config(services.store, world_id)
    if not cfg.get("presenceAnnounce", True):
        return

    seen: set[str] = set()
    unique_ids: list[str] = []
    for cid in summoned_ids:
        if cid and cid not in seen:
            seen.add(cid)
            unique_ids.append(cid)
    if not unique_ids:
        return

    target_scene = services.store.get_scene(target_scene_id)
    if not target_scene:
        return
    target_location = target_scene.get("locationName") or target_scene_id

    summoned_names = _display_names(services.store, world_id, unique_ids)
    summoner_name: str | None = None
    if summoner_id:
        summoner_name = _display_names(services.store, world_id, [summoner_id])[0]

    inserts: list[tuple[str, str, str | None]] = []

    if source == "operator" or not summoner_id:
        text = format_summon_announcement(
            None,
            summoned_names,
            target_location,
            perspective="operator",
        )
        if text:
            inserts.append((target_scene_id, text, None))
    elif source_scene_id and source_scene_id != target_scene_id:
        source_text = format_summon_announcement(
            summoner_name,
            summoned_names,
            target_location,
            perspective="source",
        )
        if source_text:
            inserts.append((source_scene_id, source_text, summoner_id))
        target_text = format_summon_announcement(
            summoner_name,
            summoned_names,
            target_location,
            perspective="target",
        )
        if target_text:
            inserts.append((target_scene_id, target_text, summoner_id))
    else:
        text = format_summon_announcement(
            summoner_name,
            summoned_names,
            target_location,
            perspective="source",
        )
        if text:
            scene = source_scene_id or target_scene_id
            inserts.append((scene, text, summoner_id))

    meta = _build_meta(
        summoner_id=summoner_id,
        summoned_ids=unique_ids,
        target_scene_id=target_scene_id,
        source=source,
        related_message_id=related_message_id,
    )
    meta_json = json.dumps(meta)

    for scene_id, output_text, character_id in inserts:
        role = "assistant" if character_id else "system"
        services.store.insert_message(
            {
                "messageId": str(uuid.uuid4()),
                "worldId": world_id,
                "channelKind": "scene",
                "sceneId": scene_id,
                "role": role,
                "characterId": character_id,
                "outputText": output_text,
                "reasoning": None,
                "streamStatus": "final",
                "generationJobId": None,
                "metaJson": meta_json,
                "createdAt": ISO(),
            }
        )


async def maybe_announce_summons_from_tool_log(
    services: Any,
    job: dict[str, Any],
    tool_log: list[dict[str, Any]],
    *,
    related_message_id: str | None = None,
) -> None:
    """Post deferred summon announcements after generation completes (tool / narrative)."""
    from altrasia.orchestrator.briefing_chain import extract_summon_targets

    target_scene, summoned = extract_summon_targets(tool_log)
    if not target_scene or not summoned:
        return

    source = "narrative"
    if any(
        e.get("name") == "scene_summon" and e.get("result") != "narrative_presence"
        for e in tool_log
    ):
        source = "tool"

    await announce_summon(
        services,
        world_id=job["worldId"],
        target_scene_id=target_scene,
        summoned_ids=summoned,
        summoner_id=job.get("characterId"),
        source_scene_id=job.get("sceneId"),
        source=source,  # type: ignore[arg-type]
        related_message_id=related_message_id,
    )
