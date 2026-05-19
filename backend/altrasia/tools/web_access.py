from __future__ import annotations

import json
from typing import Any, Literal

WebToolsAccess = Literal["off", "ask", "allow"]

WEB_TOOL_NAMES = frozenset({"webtools_invoke", "web_fetch_plugin"})

_VALID_ACCESS = frozenset({"off", "ask", "allow"})


def parse_web_tools_access(definition: dict[str, Any] | None) -> WebToolsAccess:
    if not definition:
        return "off"
    raw = definition.get("webToolsAccess")
    if raw is None:
        return "off"
    value = str(raw).strip().lower()
    if value in _VALID_ACCESS:
        return value  # type: ignore[return-value]
    return "off"


def parse_role_default_web_access(
    mapping: Any, scene_role: str | None
) -> WebToolsAccess | None:
    if not scene_role or not isinstance(mapping, dict):
        return None
    raw = mapping.get(scene_role)
    if raw is None:
        return None
    value = str(raw).strip().lower()
    if value in _VALID_ACCESS:
        return value  # type: ignore[return-value]
    return None


def _scene_role_for_character(
    store: Any, world_id: str, character_id: str
) -> str | None:
    for row in store.list_world_characters(world_id):
        if row.get("characterId") == character_id:
            role = row.get("sceneRole")
            return str(role) if role else None
    return None


def resolve_character_web_tools_access(
    store: Any,
    world_id: str,
    character_id: str,
    definition: dict[str, Any] | None,
) -> WebToolsAccess:
    """Effective access: explicit definition wins; else world role default; else off."""
    if definition and "webToolsAccess" in definition:
        return parse_web_tools_access(definition)
    from altrasia.world_config import get_world_config

    cfg = get_world_config(store, world_id)
    scene_role = _scene_role_for_character(store, world_id, character_id)
    role_access = parse_role_default_web_access(
        cfg.get("defaultWebToolsAccessBySceneRole"), scene_role
    )
    if role_access is not None:
        return role_access
    return "off"


def resolve_web_tools_policy(
    store: Any, world_id: str, character_id: str
) -> dict[str, bool]:
    """Per-character web tool exposure and approval requirements."""
    ch = store.get_character(character_id)
    definition: dict[str, Any] = {}
    if ch:
        try:
            definition = json.loads(ch.get("definitionJson") or "{}")
        except json.JSONDecodeError:
            definition = {}
    access = resolve_character_web_tools_access(
        store, world_id, character_id, definition
    )
    if access == "off":
        return {"exposed": False, "require_approval": False}
    if access == "ask":
        return {"exposed": True, "require_approval": True}
    return {"exposed": True, "require_approval": False}


def filter_tool_names_for_web_access(
    store: Any,
    world_id: str,
    character_id: str,
    names: set[str],
) -> set[str]:
    policy = resolve_web_tools_policy(store, world_id, character_id)
    if policy["exposed"]:
        return names
    return names - WEB_TOOL_NAMES
