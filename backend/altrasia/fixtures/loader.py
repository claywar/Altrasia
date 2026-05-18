from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from altrasia.domain.presence import PERSONA_ID, PresenceService
from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def _row_exists(store: SqlitePersistence, table: str, column: str, value: str) -> bool:
    cur = store.conn.execute(
        f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1", (value,)
    )
    return cur.fetchone() is not None


def _fixture_needs_id_remap(store: SqlitePersistence, data: dict[str, Any]) -> bool:
    """Stable fixture ids collide across reloads on the persistent operator DB."""
    for st in data.get("structures", []):
        if _row_exists(store, "Structure", "structureId", st["structureId"]):
            return True
    for sc in data.get("scenes", []):
        if _row_exists(store, "Scene", "sceneId", sc["sceneId"]):
            return True
    return False


def _remap_id(old_id: str, prefix: str) -> str:
    return f"{prefix}-{old_id}"


def _remap_fixture_data(data: dict[str, Any], world_id: str) -> dict[str, Any]:
    """Scope fixture entity ids to this world so demo can be loaded more than once."""
    prefix = world_id.split("-", 1)[0]
    out = copy.deepcopy(data)
    id_map: dict[str, str] = {}

    def map_id(old: str | None) -> str | None:
        if not old:
            return old
        if old not in id_map:
            id_map[old] = _remap_id(old, prefix)
        return id_map[old]

    for st in out.get("structures", []):
        st["structureId"] = map_id(st["structureId"])
    for ch in out.get("characters", []):
        ch["characterId"] = map_id(ch["characterId"])
    for sc in out.get("scenes", []):
        sc["sceneId"] = map_id(sc["sceneId"])
        if sc.get("structureId"):
            sc["structureId"] = map_id(sc["structureId"])
        sc["present"] = [map_id(cid) for cid in sc.get("present", [])]
        for ex in sc.get("exits", []):
            if ex.get("targetSceneId"):
                ex["targetSceneId"] = map_id(ex["targetSceneId"])
    out["activeSceneId"] = map_id(out["activeSceneId"])
    if out.get("personaSceneId"):
        out["personaSceneId"] = map_id(out["personaSceneId"])
    return out


def _delete_world(store: SqlitePersistence, world_id: str) -> None:
    store.conn.execute("DELETE FROM World WHERE worldId = ?", (world_id,))
    store.conn.commit()


def load_fixture(store: SqlitePersistence, fixture_path: Path) -> dict[str, Any]:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    world_id = raw.get("worldId") or str(uuid.uuid4())
    data = _remap_fixture_data(raw, world_id) if _fixture_needs_id_remap(store, raw) else raw
    now = ISO()
    config = dict(data.get("config", {}))
    config.setdefault("layoutDesignMode", False)
    active_scene_id = data["activeSceneId"]
    try:
        store.insert_world(
            {
                "worldId": world_id,
                "name": data.get("name", "Demo World"),
                "activeSceneId": active_scene_id,
                "defaultModelProfile": data.get("defaultModelProfile", "qwen3.6-35b-a3b"),
                "configJson": json.dumps(config),
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
            if not _row_exists(store, "Character", "characterId", cid):
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
                    "planPositionJson": json.dumps(sc["planPosition"])
                    if sc.get("planPosition")
                    else None,
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
        persona_scene = data.get("personaSceneId") or active_scene_id
        presence.join(persona_scene, PERSONA_ID)
    except Exception:
        _delete_world(store, world_id)
        raise
    return {"worldId": world_id, "name": data.get("name"), "activeSceneId": active_scene_id}


def load_fixture_by_id(store: SqlitePersistence, fixtures_dir: Path, fixture_id: str) -> dict[str, Any]:
    path = fixtures_dir / "demo-world" / f"{fixture_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_id}")
    return load_fixture(store, path)
