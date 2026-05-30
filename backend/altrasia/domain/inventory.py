from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from typing import Any

ItemDict = dict[str, Any]
InventoryDict = dict[str, Any]


def empty_inventory() -> InventoryDict:
    return {"worn": [], "held": [], "containers": []}


def parse_inventory(raw: str | dict[str, Any] | None) -> InventoryDict:
    if raw is None:
        return empty_inventory()
    data = raw if isinstance(raw, dict) else json.loads(raw or "{}")
    inv = empty_inventory()
    for slot in ("worn", "held", "containers"):
        items = data.get(slot)
        if isinstance(items, list):
            inv[slot] = [dict(i) for i in items if isinstance(i, dict)]
    for container in inv["containers"]:
        contents = container.get("contents")
        if not isinstance(contents, list):
            container["contents"] = []
        else:
            container["contents"] = [dict(i) for i in contents if isinstance(i, dict)]
    return inv


def new_item_id(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (label or "item").lower()).strip("-")[:24]
    return f"item-{slug}-{uuid.uuid4().hex[:8]}"


def format_inventory_summary(inventory: InventoryDict, *, max_labels: int = 6) -> str:
    """Short inline summary for scene framing: [worn: a; held: b; bag: c]."""
    parts: list[str] = []
    worn = [i.get("label", "?") for i in inventory.get("worn", [])][:max_labels]
    held = [i.get("label", "?") for i in inventory.get("held", [])][:max_labels]
    if worn:
        parts.append(f"worn: {', '.join(worn)}")
    if held:
        parts.append(f"held: {', '.join(held)}")
    for container in inventory.get("containers", [])[:3]:
        label = container.get("label", "bag")
        contents = [c.get("label", "?") for c in container.get("contents", [])][:max_labels]
        if contents:
            parts.append(f"{label}: {', '.join(contents)}")
        elif label:
            parts.append(f"{label}: (empty)")
    if not parts:
        return ""
    return f"[{'; '.join(parts)}]"


def format_worn_container_digest(inventory: InventoryDict) -> dict[str, str]:
    worn = ", ".join(i.get("label", "?") for i in inventory.get("worn", [])) or "(none)"
    container_bits: list[str] = []
    for c in inventory.get("containers", []):
        label = c.get("label", "bag")
        contents = ", ".join(x.get("label", "?") for x in c.get("contents", []))
        container_bits.append(f"{label}: {contents or '(empty)'}")
    return {
        "worn": worn,
        "containers": "; ".join(container_bits) if container_bits else "(none)",
    }


def format_fixture_summary(key: str, fixture: dict[str, Any]) -> str:
    label = fixture.get("label") or key
    kind = fixture.get("kind") or "fixture"
    if kind == "aggregate":
        picks = fixture.get("picksRemaining")
        if fixture.get("depleted"):
            return f"{label} (aggregate, depleted)"
        if picks is not None:
            return f"{label} (aggregate, {picks} picks left)"
        return f"{label} (aggregate)"
    if kind == "discrete":
        return f"{label} (discrete)"
    if kind == "briefing":
        return f"{label} (briefing)"
    return label


def get_member_inventory(store: Any, world_id: str, character_id: str) -> InventoryDict:
    row = store.get_world_member(world_id, character_id)
    if not row:
        return empty_inventory()
    return parse_inventory(row.get("inventoryJson"))


def set_member_inventory(
    store: Any, world_id: str, character_id: str, inventory: InventoryDict
) -> None:
    store.update_world_member(
        world_id, character_id, inventoryJson=json.dumps(inventory)
    )


def _find_item(
    inventory: InventoryDict, item_id: str
) -> tuple[str, int, ItemDict, int | None] | None:
    for slot in ("worn", "held"):
        for idx, item in enumerate(inventory.get(slot, [])):
            if item.get("itemId") == item_id:
                return slot, idx, item, None
    for cidx, container in enumerate(inventory.get("containers", [])):
        if container.get("itemId") == item_id:
            return "containers", cidx, container, None
        for idx, item in enumerate(container.get("contents", [])):
            if item.get("itemId") == item_id:
                return "containers", cidx, item, idx
    return None


def _remove_at(inventory: InventoryDict, slot: str, idx: int, inner: int | None) -> ItemDict:
    if slot == "containers" and inner is not None:
        container = inventory["containers"][idx]
        return container["contents"].pop(inner)
    return inventory[slot].pop(idx)


def _insert_item(inventory: InventoryDict, slot: str, item: ItemDict, container_idx: int | None = None) -> None:
    if slot == "held":
        inventory.setdefault("held", []).append(item)
    elif slot == "worn":
        inventory.setdefault("worn", []).append(item)
    elif slot == "container":
        if container_idx is None:
            raise ValueError("container index required")
        container = inventory["containers"][container_idx]
        contents = container.setdefault("contents", [])
        cap = container.get("containerCapacity")
        if cap is not None and len(contents) >= int(cap):
            raise ValueError("container full")
        contents.append(item)


def move_item(
    store: Any,
    *,
    world_id: str,
    character_id: str,
    item_id: str,
    to_slot: str,
    container_item_id: str | None = None,
) -> InventoryDict:
    inventory = get_member_inventory(store, world_id, character_id)
    found = _find_item(inventory, item_id)
    if not found:
        raise ValueError("item not found")
    slot, idx, item, inner = found
    _remove_at(inventory, slot, idx, inner)

    container_idx: int | None = None
    if to_slot == "container":
        if not container_item_id:
            raise ValueError("containerItemId required")
        for ci, c in enumerate(inventory.get("containers", [])):
            if c.get("itemId") == container_item_id:
                container_idx = ci
                break
        if container_idx is None:
            raise ValueError("container not found")
        _insert_item(inventory, "container", item, container_idx)
    elif to_slot in ("held", "worn"):
        _insert_item(inventory, to_slot, item)
    else:
        raise ValueError(f"invalid slot: {to_slot}")

    set_member_inventory(store, world_id, character_id, inventory)
    return inventory


def give_item(
    store: Any,
    *,
    world_id: str,
    from_character_id: str,
    to_character_id: str,
    item_id: str,
    to_slot: str = "held",
    container_item_id: str | None = None,
) -> dict[str, Any]:
    from_inv = get_member_inventory(store, world_id, from_character_id)
    found = _find_item(from_inv, item_id)
    if not found:
        raise ValueError("item not found on giver")
    slot, idx, item, inner = found
    _remove_at(from_inv, slot, idx, inner)
    set_member_inventory(store, world_id, from_character_id, from_inv)

    to_inv = get_member_inventory(store, world_id, to_character_id)
    container_idx: int | None = None
    if to_slot == "container":
        if not container_item_id:
            raise ValueError("containerItemId required")
        for ci, c in enumerate(to_inv.get("containers", [])):
            if c.get("itemId") == container_item_id:
                container_idx = ci
                break
        if container_idx is None:
            raise ValueError("recipient container not found")
        _insert_item(to_inv, "container", deepcopy(item), container_idx)
    else:
        _insert_item(to_inv, to_slot, deepcopy(item))
    set_member_inventory(store, world_id, to_character_id, to_inv)
    return {"ok": True, "itemId": item_id, "toCharacterId": to_character_id}


def fixture_from_item(item: ItemDict, key: str | None = None) -> dict[str, Any]:
    key = key or re.sub(r"[^a-z0-9]+", "-", item.get("label", "item").lower()).strip("-")
    return {
        "label": item.get("label", key),
        "kind": "discrete",
        "description": item.get("description", ""),
        "portable": True,
        "wearable": bool(item.get("wearable")),
        "sourceItemId": item.get("itemId"),
    }


def item_from_fixture(fixture: dict[str, Any], fixture_key: str) -> ItemDict:
    item: ItemDict = {
        "itemId": new_item_id(fixture.get("label", fixture_key)),
        "label": fixture.get("label", fixture_key),
        "sourceFixtureKey": fixture_key,
    }
    if fixture.get("description"):
        item["description"] = fixture["description"]
    if fixture.get("wearable"):
        item["wearable"] = True
    if fixture.get("containerCapacity") is not None:
        item["containerCapacity"] = fixture["containerCapacity"]
        item["contents"] = []
    return item


def pickup_fixture(
    store: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    fixture_key: str,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene or scene["worldId"] != world_id:
        raise ValueError("scene not found")
    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    fixture = fixtures.get(fixture_key)
    if not fixture:
        raise ValueError("fixture not found")
    kind = fixture.get("kind", "fixture")
    if kind not in ("discrete", "fixture"):
        raise ValueError("fixture not pickupable")
    if fixture.get("portable") is False:
        raise ValueError("fixture not portable")

    inventory = get_member_inventory(store, world_id, character_id)
    item = item_from_fixture(fixture, fixture_key)
    if fixture.get("wearable") or item.get("wearable"):
        inventory.setdefault("worn", []).append(item)
        slot = "worn"
    elif item.get("containerCapacity") is not None:
        inventory.setdefault("containers", []).append(item)
        slot = "containers"
    else:
        inventory.setdefault("held", []).append(item)
        slot = "held"

    del fixtures[fixture_key]
    store.update_scene(
        scene_id,
        fixturesJson=json.dumps(fixtures),
    )
    set_member_inventory(store, world_id, character_id, inventory)
    return {"ok": True, "fixtureKey": fixture_key, "itemId": item["itemId"], "slot": slot}


def place_fixture(
    store: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    item_id: str,
    fixture_key: str | None = None,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene or scene["worldId"] != world_id:
        raise ValueError("scene not found")
    inventory = get_member_inventory(store, world_id, character_id)
    found = _find_item(inventory, item_id)
    if not found:
        raise ValueError("item not found")
    slot, idx, item, inner = found
    if slot == "containers" and inner is None:
        raise ValueError("cannot place a container itself without emptying it")
    _remove_at(inventory, slot, idx, inner)
    set_member_inventory(store, world_id, character_id, inventory)

    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    key = fixture_key or re.sub(
        r"[^a-z0-9-]+", "-", item.get("label", "item").lower()
    ).strip("-")
    base = key
    n = 1
    while key in fixtures:
        key = f"{base}-{n}"
        n += 1
    fixtures[key] = fixture_from_item(item, key)
    store.update_scene(scene_id, fixturesJson=json.dumps(fixtures))
    return {"ok": True, "fixtureKey": key, "itemId": item_id}


def harvest_fixture(
    store: Any,
    *,
    world_id: str,
    scene_id: str,
    character_id: str,
    fixture_key: str,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene or scene["worldId"] != world_id:
        raise ValueError("scene not found")
    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    fixture = fixtures.get(fixture_key)
    if not fixture or fixture.get("kind") != "aggregate":
        raise ValueError("not an aggregate fixture")
    if fixture.get("depleted"):
        raise ValueError("fixture depleted")
    picks = int(fixture.get("picksRemaining", 0))
    if picks <= 0:
        fixture["depleted"] = True
        store.update_scene(scene_id, fixturesJson=json.dumps(fixtures))
        raise ValueError("no picks remaining")

    yield_spec = fixture.get("yield") or {"label": fixture.get("label", fixture_key)}
    item = {
        "itemId": new_item_id(yield_spec.get("label", fixture_key)),
        "label": yield_spec.get("label", fixture.get("label", fixture_key)),
        "sourceFixtureKey": fixture_key,
    }
    if yield_spec.get("description"):
        item["description"] = yield_spec["description"]

    inventory = get_member_inventory(store, world_id, character_id)
    inventory.setdefault("held", []).append(item)
    set_member_inventory(store, world_id, character_id, inventory)

    fixture["picksRemaining"] = picks - 1
    if fixture["picksRemaining"] <= 0:
        fixture["depleted"] = True
    store.update_scene(scene_id, fixturesJson=json.dumps(fixtures))
    return {
        "ok": True,
        "fixtureKey": fixture_key,
        "itemId": item["itemId"],
        "picksRemaining": fixture.get("picksRemaining"),
        "depleted": bool(fixture.get("depleted")),
    }


def replenish_fixture(
    store: Any,
    *,
    scene_id: str,
    fixture_key: str,
    picks_remaining: int | None = None,
) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    fixture = fixtures.get(fixture_key)
    if not fixture or fixture.get("kind") != "aggregate":
        raise ValueError("not an aggregate fixture")
    if picks_remaining is not None:
        fixture["picksRemaining"] = picks_remaining
    else:
        fixture["picksRemaining"] = fixture.get("defaultPicks") or 3
    fixture["depleted"] = False
    store.update_scene(scene_id, fixturesJson=json.dumps(fixtures))
    return {"ok": True, "fixtureKey": fixture_key, "picksRemaining": fixture["picksRemaining"]}


def describe_fixture(store: Any, *, scene_id: str, fixture_key: str) -> dict[str, Any]:
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    fixture = fixtures.get(fixture_key)
    if not fixture:
        raise ValueError("fixture not found")
    return {"ok": True, "fixtureKey": fixture_key, "fixture": fixture}


def get_outfit_presets(store: Any, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        return {}
    cfg = json.loads(world.get("configJson") or "{}")
    presets = cfg.get("outfitPresets")
    return presets if isinstance(presets, dict) else {}


def set_outfit_presets(store: Any, world_id: str, presets: dict[str, Any]) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    cfg = json.loads(world.get("configJson") or "{}")
    cfg["outfitPresets"] = presets
    store.update_world(world_id, configJson=json.dumps(cfg))
    return presets


def apply_outfit_preset(
    store: Any,
    *,
    world_id: str,
    character_id: str,
    preset_id: str,
) -> dict[str, Any]:
    """OP-1–4: merge or replace worn (and optional held) from world config preset."""
    presets = get_outfit_presets(store, world_id)
    preset = presets.get(preset_id)
    if not preset:
        raise ValueError("preset not found")
    inventory = get_member_inventory(store, world_id, character_id)
    replace_worn = preset.get("replaceWorn", True)
    if replace_worn:
        inventory["worn"] = []
    else:
        preset_labels = {p.get("label") for p in (preset.get("worn") or [])}
        inventory["worn"] = [
            i for i in inventory.get("worn", []) if i.get("label") not in preset_labels
        ]
    for item in preset.get("worn") or []:
        new_item = dict(item)
        if not new_item.get("itemId"):
            new_item["itemId"] = new_item_id(new_item.get("label", "item"))
        new_item.setdefault("wearable", True)
        inventory.setdefault("worn", []).append(new_item)
    for item in preset.get("held") or []:
        new_item = dict(item)
        if not new_item.get("itemId"):
            new_item["itemId"] = new_item_id(new_item.get("label", "item"))
        inventory.setdefault("held", []).append(new_item)
    set_member_inventory(store, world_id, character_id, inventory)
    return {"ok": True, "presetId": preset_id, "inventory": inventory}
