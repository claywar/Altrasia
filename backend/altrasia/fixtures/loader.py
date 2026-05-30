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
    return (
        store.fetchone(f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1", (value,))
        is not None
    )


def _delete_world(store: SqlitePersistence, world_id: str) -> None:
    # MapArtifact/MediaAsset migrations omit ON DELETE CASCADE (004_map_artifacts.sql).
    # Scene/Structure are deleted explicitly so purge stays correct if FK enforcement is off.
    with store.transaction() as conn:
        conn.execute("DELETE FROM MapArtifact WHERE worldId = ?", (world_id,))
        conn.execute("DELETE FROM MediaAsset WHERE worldId = ?", (world_id,))
        conn.execute("DELETE FROM Scene WHERE worldId = ?", (world_id,))
        conn.execute("DELETE FROM Structure WHERE worldId = ?", (world_id,))
        conn.execute("DELETE FROM World WHERE worldId = ?", (world_id,))


def _fixture_structure_ids(data: dict[str, Any]) -> list[str]:
    ids = [st["structureId"] for st in data.get("structures", [])]
    for placement in (data.get("worldMap") or {}).get("structurePlacements", []):
        sid = placement.get("structureId")
        if sid:
            ids.append(sid)
    return list(dict.fromkeys(ids))


def _fixture_scene_ids(data: dict[str, Any]) -> list[str]:
    return [sc["sceneId"] for sc in data.get("scenes", [])]


def _purge_fixture_stable_ids(store: SqlitePersistence, data: dict[str, Any]) -> None:
    """Drop fixture-owned stable ids that can outlive world delete (partial failed loads)."""
    scene_ids = _fixture_scene_ids(data)
    structure_ids = _fixture_structure_ids(data)
    if not scene_ids and not structure_ids:
        return
    with store.transaction() as conn:
        if scene_ids:
            placeholders = ",".join("?" * len(scene_ids))
            conn.execute(
                f"DELETE FROM MapArtifact WHERE sceneId IN ({placeholders})",
                scene_ids,
            )
            conn.execute(
                f"DELETE FROM Message WHERE sceneId IN ({placeholders})",
                scene_ids,
            )
            conn.execute(
                f"DELETE FROM Scene WHERE sceneId IN ({placeholders})",
                scene_ids,
            )
        if structure_ids:
            placeholders = ",".join("?" * len(structure_ids))
            conn.execute(
                f"DELETE FROM Structure WHERE structureId IN ({placeholders})",
                structure_ids,
            )


def _purge_fixture_entity_loci(store: SqlitePersistence, data: dict[str, Any]) -> None:
    with store.transaction() as conn:
        for sc in data.get("scenes", []):
            sid = sc["sceneId"]
            conn.execute(
                "DELETE FROM Locus WHERE pool = 'world' AND ownerId = ?",
                (sid,),
            )
            conn.execute(
                "DELETE FROM EvidenceRecord WHERE pool = 'world' AND ownerId = ?",
                (sid,),
            )
        for ch in data.get("characters", []):
            cid = ch["characterId"]
            conn.execute(
                "DELETE FROM Locus WHERE pool = 'mind' AND ownerId = ?",
                (cid,),
            )
            conn.execute("DELETE FROM DiarySegment WHERE characterId = ?", (cid,))
            conn.execute(
                "DELETE FROM EvidenceRecord WHERE pool = 'mind' AND ownerId = ?",
                (cid,),
            )
            conn.execute(
                "DELETE FROM EmbeddingRecord WHERE ownerScope = 'mind' AND sourceId LIKE ?",
                (f"{cid}:%",),
            )


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
    _purge_fixture_stable_ids(store, data)
    _purge_fixture_entity_loci(store, data)


def _seed_cto_team_locus(
    store: SqlitePersistence,
    world_id: str,
    characters: list[dict[str, Any]],
    now: str,
) -> None:
    """Belt-and-suspenders team roster for CTO mind recall."""
    cto = next((c for c in characters if c.get("sceneRole") == "cto"), None)
    if not cto:
        return
    directors = [
        c["displayName"]
        for c in characters
        if c.get("sceneRole") == "director"
    ]
    leads = [
        c["displayName"]
        for c in characters
        if c.get("sceneRole") not in ("cto", "director", None)
        and "reports to Jordan" in " ".join(
            loc.get("value", "") for loc in c.get("mindLoci", []) if loc.get("key") == "role"
        )
    ][:6]
    names = directors + leads
    if not names:
        return
    value = "Key reports and directors: " + ", ".join(sorted(set(names)))
    store.upsert_locus("mind", cto["characterId"], "team", value, now)


def _upsert_fixture_structure(
    store: SqlitePersistence,
    st: dict[str, Any],
    world_id: str,
    now: str,
) -> None:
    sid = st["structureId"]
    row = (
        st.get("displayName", sid),
        st.get("kind", "building"),
        json.dumps(st["boundary"]) if st.get("boundary") else None,
        now,
        world_id,
        sid,
    )
    if _row_exists(store, "Structure", "structureId", sid):
        store.run(
            """UPDATE Structure SET displayName = ?, kind = ?, boundaryJson = ?,
               updatedAt = ?, worldId = ? WHERE structureId = ?""",
            row,
        )
        store.commit()
    else:
        store.insert_structure(
            {
                "structureId": sid,
                "worldId": world_id,
                "displayName": row[0],
                "kind": row[1],
                "boundaryJson": row[2],
                "updatedAt": now,
            }
        )


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
        store.run(
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
        store.commit()
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
            _upsert_fixture_structure(store, st, world_id, now)
        for ch in data.get("characters", []):
            cid = ch["characterId"]
            _upsert_fixture_character(store, ch, now)
            member_kw: dict[str, Any] = {"sceneRole": ch.get("sceneRole")}
            if ch.get("inventory"):
                member_kw["inventoryJson"] = ch["inventory"]
            store.add_world_member(world_id, cid, **member_kw)
            for loc in ch.get("mindLoci", []):
                store.upsert_locus("mind", cid, loc["key"], loc["value"], now)
        _seed_cto_team_locus(store, world_id, data.get("characters", []), now)
        for sc in data.get("scenes", []):
            hints = {
                k: sc[k]
                for k in (
                    "mapPosition",
                    "mapZone",
                    "mapShape",
                    "mapSize",
                    "structureId",
                    "levelIndex",
                    "mapLevel",
                    "levelLabel",
                )
                if k in sc
            }
            map_art = sc.get("mapArtifact")
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
                    "mapArtifactJson": json.dumps(map_art) if map_art else None,
                    "locationName": sc["locationName"],
                    "locationDescription": sc.get("locationDescription", ""),
                    "presentJson": json.dumps(sc.get("present", [])),
                    "fixturesJson": json.dumps(sc.get("fixtures", {})),
                    "sharedStashJson": json.dumps(sc.get("sharedStash", {})),
                    "exitsJson": json.dumps(sc.get("exits", [])),
                    "activityJson": None,
                    "roundRobinIndex": 0,
                    "layoutHintsJson": json.dumps(hints) if hints else None,
                    "updatedAt": now,
                }
            )
            for key, val in sc.get("worldLoci", {}).items():
                store.upsert_locus("world", sc["sceneId"], key, val, now)
            if map_art:
                from altrasia.map_artifacts import put_artifact

                put_artifact(
                    store,
                    world_id=world_id,
                    kind="floor",
                    payload=map_art,
                    scene_id=sc["sceneId"],
                )
        presence = PresenceService(store)
        persona_scene = data.get("personaSceneId") or active_scene_id
        presence.join(persona_scene, PERSONA_ID)
        from altrasia.memory.fixture_sync import sync_scene_fixtures_to_loci

        for sc in data.get("scenes", []):
            sync_scene_fixtures_to_loci(store, scene_id=sc["sceneId"])
    except Exception:
        _delete_world(store, world_id)
        raise
    return {"worldId": world_id, "name": data.get("name"), "activeSceneId": active_scene_id}


def load_fixture_by_id(store: SqlitePersistence, fixtures_dir: Path, fixture_id: str) -> dict[str, Any]:
    path = fixtures_dir / "demo-world" / f"{fixture_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"fixture not found: {fixture_id}")
    return load_fixture(store, path)


def reset_fixture_world(
    store: SqlitePersistence, fixtures_dir: Path, world_id: str
) -> dict[str, Any]:
    """Reload the fixture backing this world (chat, runtime memory, diary cleared)."""
    world = store.get_world(world_id)
    if not world:
        raise ValueError("world not found")
    cfg = dict(json.loads(world.get("configJson") or "{}"))
    fixture_id = cfg.get("loadedFixtureId")
    if not fixture_id and not cfg.get("demoMapShowcase"):
        raise ValueError("world is not loaded from a resettable fixture")
    return load_fixture_by_id(store, fixtures_dir, fixture_id or "demo-spatial-v1")
