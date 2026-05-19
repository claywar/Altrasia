from __future__ import annotations

from typing import Any

from altrasia.memory.org_recall import can_summon_others
from altrasia.world_config import get_world_config

CAST_SCENE_READ_TOOLS = frozenset(
    {"character_list", "scene_location_list", "scene_join", "scene_summon"}
)
CAST_SCENE_SELF_TOOLS = frozenset({"scene_join"})
CAST_SCENE_SUMMON_TOOLS = frozenset({"scene_summon"})
OBSERVER_ONLY_SCENE_TOOLS = frozenset(
    {"scene_exit_set_state", "scene_update_fixture"}
)
# Ambient generations: no summoning others; self-move only via scene_join.
AMBIENT_MOVEMENT_TRIGGERS = frozenset({"idle_timer"})


def narrative_presence_eligible(trigger: str | None) -> bool:
    """Narrative auto-move applies only on reactive play, not ambient idle ticks."""
    return str(trigger or "") not in AMBIENT_MOVEMENT_TRIGGERS


def cast_allowed_tool_names(
    store: Any,
    world_id: str,
    character_id: str,
    *,
    trigger: str | None = None,
) -> set[str] | None:
    """Return allowed tool names for cast generation, or None for default memory-only filter."""
    cfg = get_world_config(store, world_id)
    members = store.list_world_characters(world_id)
    speaker = next((m for m in members if m["characterId"] == character_id), None)
    scene_role = speaker.get("sceneRole") if speaker else None

    allowed: set[str] = set()
    if cfg.get("castSummonEnabled", True):
        allowed |= {"character_list", "scene_location_list", "scene_join"}
        if (
            trigger not in AMBIENT_MOVEMENT_TRIGGERS
            and can_summon_others(cfg, scene_role)
        ):
            allowed.add("scene_summon")
    if cfg.get("discussionSignalsEnabled", True):
        allowed.add("discussion_signal")
    if not allowed:
        return None
    return allowed
