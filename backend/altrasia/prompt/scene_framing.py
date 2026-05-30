from __future__ import annotations

import json
from typing import Any

from altrasia.domain.presence import PERSONA_ID, PresenceService
from altrasia.debate_activity import format_activity_summary
from altrasia.domain.inventory import (
    format_fixture_summary,
    format_inventory_summary,
    get_member_inventory,
)
from altrasia.domain.shared_stash import format_stash_summary, parse_shared_stash
from altrasia.memory.org_recall import is_leadership_role
from altrasia.persistence.sqlite_store import SqlitePersistence


def build_scene_framing(
    store: SqlitePersistence,
    presence: PresenceService,
    *,
    world_id: str,
    character_id: str,
    scene_id: str,
) -> str:
    """PI-4 / LP-3: present cast with inventory, fixtures, elsewhere roster for leaders."""
    scene = store.get_scene(scene_id)
    if not scene:
        return ""

    members = {m["characterId"]: m for m in store.list_world_characters(world_id)}
    speaker = members.get(character_id, {})
    leadership = is_leadership_role(speaker.get("sceneRole"))

    present_ids = [
        c for c in PresenceService.parse_present(scene.get("presentJson", "[]"))
        if c != PERSONA_ID
    ]
    lines = [
        f"[Scene — {scene.get('locationName', scene_id)}]",
        (scene.get("locationDescription") or "").strip(),
    ]

    activity_line = format_activity_summary(scene, members=members)
    if activity_line:
        lines.append(activity_line)

    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    if fixtures:
        fixture_parts = [
            format_fixture_summary(k, fixtures[k])
            for k in sorted(fixtures.keys())[:12]
        ]
        lines.append(f"Fixtures: {', '.join(fixture_parts)}")

    stash = parse_shared_stash(scene.get("sharedStashJson"))
    stash_line = format_stash_summary(stash)
    if stash_line:
        lines.append(stash_line)

    if present_ids:
        present_bits: list[str] = []
        for cid in present_ids:
            ch = members.get(cid, {"displayName": cid})
            label = ch.get("displayName", cid)
            role = ch.get("sceneRole")
            inv = get_member_inventory(store, world_id, cid)
            inv_summary = format_inventory_summary(inv)
            bit = label
            if role:
                bit = f"{label} ({role})"
            if inv_summary:
                bit = f"{bit} {inv_summary}"
            present_bits.append(bit)
        lines.append(f"Present: {', '.join(present_bits)}")
    else:
        lines.append("Present: (no other cast in this room)")

    if leadership:
        roster = presence.roster(world_id)
        elsewhere = [
            e
            for e in roster.get("elsewhere", [])
            if e["characterId"] != character_id
        ]
        unplaced = roster.get("unplaced", [])
        if elsewhere or unplaced:
            lines.append("Elsewhere (available to summon):")
            for entry in elsewhere + unplaced:
                if entry["characterId"] == character_id:
                    continue
                ch = members.get(entry["characterId"], {})
                role = ch.get("sceneRole") or "member"
                loc = entry.get("locationName") or "(unplaced)"
                sid = entry.get("sceneId")
                sid_part = f", sceneId={sid}" if sid else ""
                lines.append(
                    f"- {entry.get('displayName', entry['characterId'])} ({role}) @ {loc}{sid_part}"
                )

    scenes = store.list_scenes(world_id)
    if leadership and len(scenes) > 1:
        lines.append("Locations in this world:")
        for sc in sorted(scenes, key=lambda s: s.get("locationName", "")):
            lines.append(f"- {sc['sceneId']}: {sc['locationName']}")

    return "\n".join(line for line in lines if line).strip()
