from __future__ import annotations

import json
from typing import Any

from altrasia.domain.narrative_presence import implies_briefing

MOVEMENT_TOOLS = frozenset({"scene_join", "scene_summon"})


def movement_tools_ran(tool_log: list[dict[str, Any]]) -> bool:
    """True when the model invoked movement tools (not narrative auto-summon)."""
    return any(
        entry.get("name") in MOVEMENT_TOOLS
        and entry.get("result") != "narrative_presence"
        for entry in tool_log
    )


def extract_summon_targets(tool_log: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    """Return (target_scene_id, summoned_character_ids) from tool log."""
    target: str | None = None
    summoned: list[str] = []
    for entry in tool_log:
        if entry.get("name") != "scene_summon":
            continue
        args = entry.get("arguments") or {}
        target = args.get("targetSceneId") or target
        summoned.extend(args.get("characterIds") or [])
    return target, summoned


def sort_briefing_speakers(
    store: Any, world_id: str, character_ids: list[str]
) -> list[str]:
    """Directors before ICs for briefing follow-up."""
    members = {m["characterId"]: m for m in store.list_world_characters(world_id)}
    priority = {"director": 0, "cto": 1}

    def key(cid: str) -> tuple[int, str]:
        role = (members.get(cid) or {}).get("sceneRole") or "zzz"
        return (priority.get(role, 2), (members.get(cid) or {}).get("displayName") or cid)

    return sorted(character_ids, key=key)


async def maybe_enqueue_briefing_followups(
    orch: Any,
    job: dict[str, Any],
    tool_log: list[dict[str, Any]],
) -> None:
    """After summon + briefing persona line, enqueue capped NPC replies at target scene."""
    if job.get("trigger") != "persona_message":
        return
    if not movement_tools_ran(tool_log):
        return

    trigger_msg_id = job.get("triggerMessageId")
    if not trigger_msg_id:
        return
    msg = orch.svc.store.fetchone(
        "SELECT outputText FROM Message WHERE messageId = ?",
        (trigger_msg_id,),
    )
    if not msg or not implies_briefing(msg["outputText"] or ""):
        return

    target_scene, summoned = extract_summon_targets(tool_log)
    if not target_scene or not summoned:
        return

    cfg = json.loads(orch.svc.store.get_world(job["worldId"]).get("configJson") or "{}")
    max_replies = int(cfg.get("briefingMaxReplies", 2))
    speaker_id = job["characterId"]
    candidates = [c for c in summoned if c != speaker_id]
    candidates = sort_briefing_speakers(orch.svc.store, job["worldId"], candidates)[:max_replies]

    depth = int(job.get("continueDepth") or 0)
    max_depth = int(cfg.get("maxContinueDepth", 2))
    for cid in candidates:
        if depth + 1 > max_depth:
            break
        await orch.enqueue_generation(
            world_id=job["worldId"],
            scene_id=target_scene,
            character_id=cid,
            trigger="briefing_followup",
            continue_depth=depth + 1,
            trigger_message_id=trigger_msg_id,
        )
        depth += 1
