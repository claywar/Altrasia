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
    access = parse_web_tools_access(definition)
    if access == "off":
        return {"exposed": False, "require_approval": False}
    if access == "ask":
        return {"exposed": True, "require_approval": True}
    # allow: profile overrides world — never require approval
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
