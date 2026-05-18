from __future__ import annotations

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


def _delete_world(store: SqlitePersistence, world_id: str) -> None:
    store.conn.execute("DELETE FROM World WHERE worldId = ?", (world_id,))
    store.conn.commit()


def _purge_fixture_entity_loci(store: SqlitePersistence, data: dict[str, Any]) -> None:
    for sc in data.get("scenes", []):
        store.conn.execute(
            "DELETE FROM Locus WHERE pool = 'world' AND ownerId = ?",
            (sc["sceneId"],),
        )
    for ch in data.get("characters", []):
        store.conn.execute(
            "DELETE FROM Locus WHERE pool = 'mind' AND ownerId = ?",
            (ch["characterId"],),
        )
    store.conn.commit()


def purge_fixture_installation(
    store: SqlitePersistence, fixture_id: str, data: dict[str, Any]
) -> None:
    """Drop prior loads of this fixture so each load starts from a clean slate."""
    to_delete: set[str] = set()
    stable_wid = data.get("worldId")
    if stable_wid:
        to_delete.add(stable_wid)
    fixture_demo = (data.get("config") or {}).get("demoMapShowcase")
    for w in store.list_worlds():
        cfg = json.loads(w.get("configJson") or "{}")
        if cfg.get("loadedFixtureId") == fixture_id:
            to_delete.add(w["worldId"])
        elif fixture_demo and cfg.get("demoMapShowcase"):
            to_delete.add(w["worldId"])
    for wid in to_delete:
        if store.get_world(wid):
            _delete_world(store, wid)
    _purge_fixture_entity_loci(store, data)


def _upsert_fixture_character(
    store: SqlitePersistence, ch: dict[str, Any], now: str
) -> None:
    cid = ch["characterId"]
    row = {
        "characterId": cid,
        "displayName": ch["displayName"],
        "definitionJson": json.dumps(ch.get("definition", {})),
        "modelProfile": ch.get("modelProfile", "qwen3.6-35b-a3b"),
        "speechWeight": ch.get("speechWeight", 0.5),
        "createdAt": now,
    }
    if _row_exists(store, "Character", "characterId", cid):
        store.conn.execute(
            """UPDATE Character SET displayName = ?, definitionJson = ?,
               modelProfile = ?, speechWeight = ? WHERE characterId = ?""",
            (
                row["displayName"],
                row["definitionJson"],
                row["modelProfile"],
                row["speechWeight"],
                cid,
            ),
        )
        store.conn.commit()
    else:
        store.insert_character(row)


def load_fixture(store: SqlitePersistence, fixture_path: Path) -> dict[str, Any]:
    raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_id = raw.get("fixtureId") or fixture_path.stem
    purge_fixture_installation(store, fixture_id, raw)

    world_id = raw.get("worldId") or str(uuid.uuid4())
    data = raw
    now = ISO()
    config = dict(data.get("config", {}))
    config.setdefault("layoutDesignMode", False)
    config["loadedFixtureId"] = fixture_id
    active_scene_id = data["activeSceneId"]
    try:
        store.insert_world(
            {
                "worldId": world_id,
                "name": data.get("name", "Demo World"),
                "activeSceneId": active_scene_id,
                "defaultModelProfile": data.get("defaultModelProfile", "qwen3.6-35b-a3b"),
                "configJson": json.dumps(config),
                "worldMapJson": json.dumps(data["worldMap"])
                if data.get("worldMap")
                else None,
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
            _upsert_fixture_character(store, ch, now)
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
