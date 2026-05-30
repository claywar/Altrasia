from __future__ import annotations

import json
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

PERSONA_ID = "__persona__"


class PresenceService:
    def __init__(self, store: SqlitePersistence) -> None:
        self.store = store

    @staticmethod
    def parse_present(raw: str) -> list[str]:
        return json.loads(raw or "[]")

    @staticmethod
    def dump_present(ids: list[str]) -> str:
        return json.dumps(ids)

    def join(self, scene_id: str, character_id: str) -> None:
        """LP-1: join removes from other scenes in same world."""
        scene = self.store.get_scene(scene_id)
        if not scene:
            raise ValueError("scene not found")
        world_id = scene["worldId"]
        for other in self.store.list_scenes(world_id):
            present = self.parse_present(other["presentJson"])
            if character_id in present:
                present.remove(character_id)
                self.store.update_scene(
                    other["sceneId"], presentJson=self.dump_present(present)
                )
        present = self.parse_present(scene["presentJson"])
        if character_id not in present:
            present.append(character_id)
        self.store.update_scene(scene_id, presentJson=self.dump_present(present))

    def leave(self, scene_id: str, character_id: str) -> None:
        scene = self.store.get_scene(scene_id)
        if not scene:
            raise ValueError("scene not found")
        present = self.parse_present(scene["presentJson"])
        if character_id in present:
            present.remove(character_id)
        self.store.update_scene(scene_id, presentJson=self.dump_present(present))

    def roster(self, world_id: str) -> dict[str, list[dict[str, Any]]]:
        """CC-3: elsewhere roster includes presentSceneId for cast not in active scene."""
        from altrasia.domain.inventory import format_inventory_summary, get_member_inventory

        world = self.store.get_world(world_id)
        active_scene_id = world["activeSceneId"] if world else None
        scenes = self.store.list_scenes(world_id)
        chars = {c["characterId"]: c for c in self.store.list_world_characters(world_id)}

        def _inv_summary(cid: str) -> str:
            return format_inventory_summary(get_member_inventory(self.store, world_id, cid))

        at_location: list[dict] = []
        elsewhere: list[dict] = []
        placed_ids: set[str] = set()
        for scene in scenes:
            for cid in self.parse_present(scene["presentJson"]):
                if cid == PERSONA_ID:
                    continue
                placed_ids.add(cid)
                ch = chars.get(cid, {"characterId": cid, "displayName": cid})
                entry = {
                    "characterId": cid,
                    "displayName": ch.get("displayName", cid),
                    "sceneId": scene["sceneId"],
                    "locationName": scene["locationName"],
                    "presentSceneId": scene["sceneId"],
                    "inventorySummary": _inv_summary(cid),
                }
                if scene["sceneId"] == active_scene_id:
                    at_location.append(entry)
                else:
                    elsewhere.append(entry)
        unplaced: list[dict] = []
        for cid, ch in chars.items():
            if cid not in placed_ids and not ch.get("disabled"):
                unplaced.append(
                    {
                        "characterId": cid,
                        "displayName": ch["displayName"],
                        "sceneId": None,
                        "locationName": None,
                        "presentSceneId": None,
                        "inventorySummary": _inv_summary(cid),
                    }
                )
        return {
            "atLocation": at_location,
            "elsewhere": elsewhere,
            "muted": [c for c in chars.values() if c.get("muted")],
            "unplaced": unplaced,
        }
