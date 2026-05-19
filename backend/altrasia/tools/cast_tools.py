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


def cast_allowed_tool_names(
    store: Any, world_id: str, character_id: str
) -> set[str] | None:
    """Return allowed tool names for cast generation, or None for default memory-only filter."""
    cfg = get_world_config(store, world_id)
    members = store.list_world_characters(world_id)
    speaker = next((m for m in members if m["characterId"] == character_id), None)
    scene_role = speaker.get("sceneRole") if speaker else None

    allowed: set[str] = set()
    if cfg.get("castSummonEnabled", True):
        allowed |= {"character_list", "scene_location_list", "scene_join"}
        if can_summon_others(cfg, scene_role):
            allowed.add("scene_summon")
    if not allowed:
        return None
    return allowed
