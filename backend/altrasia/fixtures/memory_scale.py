"""Seed synthetic memory-scale datasets (docs/17 §7)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()

_PROFILES: dict[str, dict[str, int]] = {
    "ci": {
        "characters": 24,
        "diary_segments_total": 1200,
        "mind_loci_per_character": 40,
        "world_loci_per_scene": 20,
        "scenes": 3,
    },
    "reference": {
        "characters": 24,
        "diary_segments_total": 12000,
        "mind_loci_per_character": 200,
        "world_loci_per_scene": 100,
        "scenes": 6,
    },
}


def seed_memory_scale(store: Any, *, profile: str = "ci") -> dict[str, Any]:
    """Populate an empty migrated DB with scale data. Returns metadata for tests."""
    spec = _PROFILES[profile]
    n_chars = spec["characters"]
    n_scenes = spec["scenes"]
    diary_total = spec["diary_segments_total"]
    diary_per = max(1, diary_total // n_chars)
    now = datetime.now(timezone.utc)

    world_id = str(uuid.uuid4())
    store.insert_world(
        {
            "worldId": world_id,
            "name": f"Memory scale ({profile})",
            "activeSceneId": None,
            "defaultModelProfile": "qwen3.6-35b-a3b",
            "configJson": json.dumps({"mandatoryRecallMaxChars": 12000}),
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": ISO(),
            "updatedAt": ISO(),
        }
    )

    scene_ids: list[str] = []
    for i in range(n_scenes):
        sid = f"scale-scene-{i}"
        scene_ids.append(sid)
        store.conn.execute(
            """INSERT INTO Scene (sceneId, worldId, locationName, locationDescription,
               presentJson, fixturesJson, exitsJson, updatedAt)
               VALUES (?, ?, ?, ?, '[]', '{}', '[]', ?)""",
            (sid, world_id, f"Scene {i}", f"Scale scene {i}", ISO()),
        )
    store.conn.execute(
        "UPDATE World SET activeSceneId = ? WHERE worldId = ?",
        (scene_ids[0], world_id),
    )

    char_ids: list[str] = []
    for i in range(n_chars):
        cid = f"scale-char-{i:02d}"
        char_ids.append(cid)
        store.insert_character(
            {
                "characterId": cid,
                "displayName": f"Scale {i}",
                "definitionJson": json.dumps({"personality": f"Character {i}"}),
                "modelProfile": "qwen3.6-35b-a3b",
                "speechWeight": 0.5,
                "createdAt": ISO(),
            }
        )
        store.add_world_member(world_id, cid)
        secret = f"SECRET_TOKEN_{cid}_ONLY"
        store.upsert_locus("mind", cid, "private_fact", secret, ISO())
        for k in range(spec["mind_loci_per_character"] - 1):
            store.upsert_locus(
                "mind",
                cid,
                f"fact-{k}",
                f"Fact {k} for {cid} with keyword alpha{k % 17} beta{i}",
                ISO(),
            )
        for d in range(diary_per):
            ts = (now - timedelta(minutes=diary_per - d)).isoformat()
            store.append_diary(
                {
                    "segmentId": str(uuid.uuid4()),
                    "characterId": cid,
                    "text": f"Diary entry {d} for {cid} scene {scene_ids[d % n_scenes]}",
                    "sourceSceneId": scene_ids[d % n_scenes],
                    "messageIdsJson": "[]",
                    "dedupeKey": f"{cid}-{d}",
                    "kind": "witnessed",
                    "createdAt": ts,
                }
            )

    for sid in scene_ids:
        for w in range(spec["world_loci_per_scene"]):
            store.upsert_locus(
                "world",
                sid,
                f"ambience-{w}",
                f"World fact {w} for {sid}",
                ISO(),
            )

    store.conn.commit()
    return {
        "worldId": world_id,
        "sceneIds": scene_ids,
        "characterIds": char_ids,
        "profile": profile,
    }
