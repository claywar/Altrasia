"""DM-4 world package export/import (JSON snapshot in zip)."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PACKAGE_FORMAT = "altrasia-world-package"
PACKAGE_VERSION = 1


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_all(store: Any, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    cur = store.conn.execute(sql, params)
    return store._rows(cur.fetchall())


def _collect_snapshot(store: Any, world_id: str) -> dict[str, Any]:
    world = store.get_world(world_id)
    if not world:
        raise ValueError(f"world not found: {world_id}")
    scenes = store.list_scenes(world_id)
    scene_ids = [s["sceneId"] for s in scenes]
    members = _fetch_all(store, "SELECT * FROM WorldMember WHERE worldId = ?", (world_id,))
    char_ids = [m["characterId"] for m in members]
    characters = [store.get_character(cid) for cid in char_ids]
    characters = [c for c in characters if c]
    structures = _fetch_all(store, "SELECT * FROM Structure WHERE worldId = ?", (world_id,))
    messages = _fetch_all(store, "SELECT * FROM Message WHERE worldId = ?", (world_id,))
    signals = _fetch_all(store, "SELECT * FROM CrossSceneSignal WHERE worldId = ?", (world_id,))
    channels = _fetch_all(store, "SELECT * FROM CommChannel WHERE worldId = ?", (world_id,))
    loci: list[dict[str, Any]] = []
    if scene_ids:
        ph = ",".join("?" * len(scene_ids))
        loci.extend(
            _fetch_all(
                store,
                f"SELECT * FROM Locus WHERE pool = 'world' AND ownerId IN ({ph})",
                tuple(scene_ids),
            )
        )
    if char_ids:
        ph = ",".join("?" * len(char_ids))
        loci.extend(
            _fetch_all(
                store,
                f"SELECT * FROM Locus WHERE pool = 'mind' AND ownerId IN ({ph})",
                tuple(char_ids),
            )
        )
    diary: list[dict[str, Any]] = []
    if char_ids:
        ph = ",".join("?" * len(char_ids))
        diary = _fetch_all(
            store,
            f"SELECT * FROM DiarySegment WHERE characterId IN ({ph})",
            tuple(char_ids),
        )
    return {
        "world": world,
        "scenes": scenes,
        "structures": structures,
        "worldMembers": members,
        "characters": characters,
        "messages": messages,
        "loci": loci,
        "diarySegments": diary,
        "signals": signals,
        "commChannels": channels,
    }


def export_world_package(
    store: Any, world_id: str, *, assets_dir: Path | None = None
) -> bytes:
    snapshot = _collect_snapshot(store, world_id)
    manifest = {
        "format": PACKAGE_FORMAT,
        "version": PACKAGE_VERSION,
        "exportedAt": _iso(),
        "sourceWorldId": world_id,
        "worldName": snapshot["world"]["name"],
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        zf.writestr("snapshot.json", json.dumps(snapshot, indent=2))
        if assets_dir:
            world_assets = assets_dir / world_id
            if world_assets.is_dir():
                for path in world_assets.rglob("*"):
                    if path.is_file():
                        zf.write(path, f"assets/{path.relative_to(world_assets).as_posix()}")
    return buf.getvalue()


def import_world_package(
    store: Any, data: bytes, *, assets_dir: Path | None = None
) -> dict[str, str]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        if manifest.get("format") != PACKAGE_FORMAT:
            raise ValueError("unsupported package format")
        snapshot = json.loads(zf.read("snapshot.json"))
        asset_names = [n for n in zf.namelist() if n.startswith("assets/") and not n.endswith("/")]

    new_world_id = str(uuid.uuid4())
    world = dict(snapshot["world"])
    old_world_id = world["worldId"]
    world["worldId"] = new_world_id
    world["eventSeq"] = 0
    world["updatedAt"] = _iso()
    if not world.get("createdAt"):
        world["createdAt"] = world["updatedAt"]

    for ch in snapshot.get("characters", []):
        store.conn.execute(
            """INSERT OR IGNORE INTO Character (characterId, displayName, definitionJson,
               modelProfile, speechWeight, createdAt)
               VALUES (:characterId, :displayName, :definitionJson, :modelProfile,
               :speechWeight, :createdAt)""",
            ch,
        )

    scene_map: dict[str, str] = {}
    for sc in snapshot.get("scenes", []):
        old_sid = sc["sceneId"]
        scene_map[old_sid] = str(uuid.uuid4())

    if world.get("activeSceneId") and world["activeSceneId"] in scene_map:
        world["activeSceneId"] = scene_map[world["activeSceneId"]]
    store.insert_world(world)

    for st in snapshot.get("structures", []):
        row = dict(st)
        row["worldId"] = new_world_id
        existing = store.conn.execute(
            "SELECT 1 FROM Structure WHERE structureId = ?", (row["structureId"],)
        ).fetchone()
        if existing:
            row["structureId"] = str(uuid.uuid4())
        store.conn.execute(
            """INSERT INTO Structure (structureId, worldId, displayName, kind, boundaryJson, updatedAt)
               VALUES (:structureId, :worldId, :displayName, :kind, :boundaryJson, :updatedAt)""",
            row,
        )

    for sc in snapshot.get("scenes", []):
        row = dict(sc)
        old_sid = sc["sceneId"]
        row["sceneId"] = scene_map[old_sid]
        row["worldId"] = new_world_id
        try:
            exits = json.loads(row.get("exitsJson") or "[]")
            for ex in exits:
                tid = ex.get("targetSceneId")
                if tid and tid in scene_map:
                    ex["targetSceneId"] = scene_map[tid]
            row["exitsJson"] = json.dumps(exits)
        except json.JSONDecodeError:
            pass
        store.insert_scene(row)

    for wm in snapshot.get("worldMembers", []):
        store.add_world_member(
            new_world_id,
            wm["characterId"],
            muted=wm.get("muted", 0),
            disabled=wm.get("disabled", 0),
            sceneRole=wm.get("sceneRole"),
            inventoryJson=wm.get("inventoryJson", "{}"),
        )

    msg_ids: dict[str, str] = {}
    for msg in snapshot.get("messages", []):
        row = dict(msg)
        old_mid = row["messageId"]
        row["messageId"] = str(uuid.uuid4())
        msg_ids[old_mid] = row["messageId"]
        row["worldId"] = new_world_id
        row["generationJobId"] = None
        if row.get("sceneId") and row["sceneId"] in scene_map:
            row["sceneId"] = scene_map[row["sceneId"]]
        store.insert_message(row)

    for loc in snapshot.get("loci", []):
        owner = loc["ownerId"]
        if loc["pool"] == "world" and owner in scene_map:
            owner = scene_map[owner]
        store.upsert_locus(
            loc["pool"], owner, loc["locusKey"], loc["value"], loc["updatedAt"]
        )

    for seg in snapshot.get("diarySegments", []):
        row = dict(seg)
        row["segmentId"] = str(uuid.uuid4())
        if row.get("sourceSceneId") in scene_map:
            row["sourceSceneId"] = scene_map[row["sourceSceneId"]]
        try:
            mids = json.loads(row.get("messageIdsJson") or "[]")
            row["messageIdsJson"] = json.dumps([msg_ids.get(m, m) for m in mids])
        except json.JSONDecodeError:
            row["messageIdsJson"] = "[]"
        store.append_diary(row)

    for sig in snapshot.get("signals", []):
        row = dict(sig)
        row["signalId"] = str(uuid.uuid4())
        row["worldId"] = new_world_id
        if row.get("sourceSceneId") in scene_map:
            row["sourceSceneId"] = scene_map[row["sourceSceneId"]]
        if row.get("targetSceneId") in scene_map:
            row["targetSceneId"] = scene_map[row["targetSceneId"]]
        store.insert_signal(row)

    for ch in snapshot.get("commChannels", []):
        row = dict(ch)
        row["worldId"] = new_world_id
        store.conn.execute(
            """INSERT INTO CommChannel (channelId, worldId, endpointsJson, participantsJson, active)
               VALUES (:channelId, :worldId, :endpointsJson, :participantsJson, :active)""",
            row,
        )

    store.conn.commit()

    if assets_dir and asset_names:
        dest = assets_dir / new_world_id
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in asset_names:
                rel = name[len("assets/") :]
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

    return {
        "worldId": new_world_id,
        "name": world["name"],
        "activeSceneId": world["activeSceneId"],
        "importedFrom": old_world_id,
    }
