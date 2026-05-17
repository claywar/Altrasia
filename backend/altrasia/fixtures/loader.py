from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from altrasia.domain.presence import PERSONA_ID, PresenceService
from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def load_fixture(store: SqlitePersistence, fixture_path: Path) -> dict[str, Any]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    world_id = data.get("worldId") or str(uuid.uuid4())
    now = ISO()
    store.insert_world(
        {
            "worldId": world_id,
            "name": data.get("name", "Demo World"),
            "activeSceneId": data["activeSceneId"],
            "defaultModelProfile": data.get("defaultModelProfile", "qwen3.6-35b-a3b"),
            "configJson": json.dumps(data.get("config", {})),
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": now,
            "updatedAt": now,
        }
    )
    for st in data.get("structures", []):
        store.insert_structure(
            {
                "structureId": st["structureId"],
                "worldId": world_id,
                "displayName": st["displayName"],
                "kind": st.get("kind", "building"),
                "boundaryJson": json.dumps(st["boundary"]) if st.get("boundary") else None,
                "updatedAt": now,
            }
        )
    for ch in data.get("characters", []):
        cid = ch["characterId"]
        store.insert_character(
            {
                "characterId": cid,
                "displayName": ch["displayName"],
                "definitionJson": json.dumps(ch.get("definition", {})),
                "modelProfile": ch.get("modelProfile", "qwen3.6-35b-a3b"),
                "speechWeight": ch.get("speechWeight", 0.5),
                "createdAt": now,
            }
        )
        store.add_world_member(world_id, cid, sceneRole=ch.get("sceneRole"))
        for loc in ch.get("mindLoci", []):
            store.upsert_locus("mind", cid, loc["key"], loc["value"], now)
    for sc in data.get("scenes", []):
        hints = {
            k: sc[k]
            for k in (
                "mapPosition",
                "mapZone",
                "mapShape",
                "mapSize",
                "structureId",
            )
            if k in sc
        }
        store.insert_scene(
            {
                "sceneId": sc["sceneId"],
                "worldId": world_id,
                "structureId": sc.get("structureId"),
                "mapLevel": sc.get("mapLevel", 0),
                "levelLabel": sc.get("levelLabel"),
                "planPositionJson": json.dumps(sc["planPosition"]) if sc.get("planPosition") else None,
                "mapArtifactJson": None,
                "locationName": sc["locationName"],
                "locationDescription": sc.get("locationDescription", ""),
                "presentJson": json.dumps(sc.get("present", [])),
                "fixturesJson": json.dumps(sc.get("fixtures", {})),
                "exitsJson": json.dumps(sc.get("exits", [])),
                "activityJson": None,
                "roundRobinIndex": 0,
                "layoutHintsJson": json.dumps(hints) if hints else None,
                "updatedAt": now,
            }
        )
        for key, val in sc.get("worldLoci", {}).items():
            store.upsert_locus("world", sc["sceneId"], key, val, now)
    presence = PresenceService(store)
    persona_scene = data.get("personaSceneId") or data["activeSceneId"]
    presence.join(persona_scene, PERSONA_ID)
    return {"worldId": world_id, "name": data.get("name"), "activeSceneId": data["activeSceneId"]}


def load_fixture_by_id(store: SqlitePersistence, fixtures_dir: Path, fixture_id: str) -> dict[str, Any]:
    path = fixtures_dir / "demo-world" / f"{fixture_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_id}")
    return load_fixture(store, path)
