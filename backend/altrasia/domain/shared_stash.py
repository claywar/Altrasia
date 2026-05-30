from __future__ import annotations

import json
from typing import Any

from altrasia.domain.inventory import (
    get_member_inventory,
    new_item_id,
    set_member_inventory,
)


def parse_shared_stash(raw: str | dict[str, Any] | None) -> dict[str, Any]:
    if raw is None:
        return {}
    data = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    if not isinstance(data, dict):
        return {}
    out: dict[str, Any] = {}
    for key, stash in data.items():
        if not isinstance(stash, dict):
            continue
        items = stash.get("items")
        if not isinstance(items, list):
            items = []
        out[key] = {
            "label": stash.get("label", key),
            "items": [dict(i) for i in items if isinstance(i, dict)],
            "capacity": stash.get("capacity"),
        }
    return out


def get_scene_stash(store: Any, scene_id: str) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        return {}
    return parse_shared_stash(scene.get("sharedStashJson"))


def set_scene_stash(store: Any, scene_id: str, stash: dict[str, Any]) -> None:
    store.update_scene(scene_id, sharedStashJson=json.dumps(stash))


def format_stash_summary(stash: dict[str, Any], *, max_stashes: int = 4) -> str:
    if not stash:
        return ""
    parts: list[str] = []
    for key in sorted(stash.keys())[:max_stashes]:
        entry = stash[key]
        label = entry.get("label", key)
        count = len(entry.get("items") or [])
        cap = entry.get("capacity")
        if cap is not None:
            parts.append(f"{label} ({count}/{cap})")
        else:
            parts.append(f"{label} ({count})")
    if not parts:
        return ""
    return f"Shared: {', '.join(parts)}"


def _stash_capacity(entry: dict[str, Any]) -> int | None:
    cap = entry.get("capacity")
    if cap is None:
        return None
    return int(cap)


def take_from_stash(
    store: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    stash_key: str,
    item_id: str | None = None,
) -> dict[str, Any]:
    stash = get_scene_stash(store, scene_id)
    entry = stash.get(stash_key)
    if not entry:
        raise ValueError("stash not found")
    items = entry.get("items") or []
    if not items:
        raise ValueError("stash empty")
    idx = 0
    if item_id:
        idx = next((i for i, it in enumerate(items) if it.get("itemId") == item_id), -1)
        if idx < 0:
            raise ValueError("item not found in stash")
    item = items.pop(idx)
    entry["items"] = items
    stash[stash_key] = entry
    set_scene_stash(store, scene_id, stash)

    inventory = get_member_inventory(store, world_id, character_id)
    inventory.setdefault("held", []).append(dict(item))
    set_member_inventory(store, world_id, character_id, inventory)
    return {"ok": True, "stashKey": stash_key, "itemId": item.get("itemId"), "slot": "held"}


def deposit_to_stash(
    store: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    stash_key: str,
    item_id: str,
) -> dict[str, Any]:
    from altrasia.domain.inventory import _find_item, _remove_at

    stash = get_scene_stash(store, scene_id)
    entry = stash.get(stash_key)
    if not entry:
        raise ValueError("stash not found")
    cap = _stash_capacity(entry)
    items = entry.get("items") or []
    if cap is not None and len(items) >= cap:
        raise ValueError("stash full")

    inventory = get_member_inventory(store, world_id, character_id)
    found = _find_item(inventory, item_id)
    if not found:
        raise ValueError("item not found on character")
    slot, idx, item, inner = found
    if slot == "containers" and inner is None:
        raise ValueError("cannot deposit a container itself")
    _remove_at(inventory, slot, idx, inner)
    set_member_inventory(store, world_id, character_id, inventory)

    items.append(dict(item))
    entry["items"] = items
    stash[stash_key] = entry
    set_scene_stash(store, scene_id, stash)
    return {"ok": True, "stashKey": stash_key, "itemId": item_id}


def add_stash_item(
    store: Any,
    *,
    scene_id: str,
    stash_key: str,
    label: str,
) -> dict[str, Any]:
    stash = get_scene_stash(store, scene_id)
    entry = stash.get(stash_key) or {"label": stash_key, "items": []}
    cap = _stash_capacity(entry)
    items = entry.get("items") or []
    if cap is not None and len(items) >= cap:
        raise ValueError("stash full")
    item = {"itemId": new_item_id(label), "label": label}
    items.append(item)
    entry["items"] = items
    if "label" not in entry:
        entry["label"] = stash_key
    stash[stash_key] = entry
    set_scene_stash(store, scene_id, stash)
    return {"ok": True, "stashKey": stash_key, "item": item}
