"""MAP-1 / MAP-11: map artifact storage and retrieval."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()


def get_scene_artifact(store: Any, world_id: str, scene_id: str) -> dict[str, Any] | None:
    row = store.fetchone(
        """SELECT jsonBlob FROM MapArtifact
           WHERE worldId = ? AND sceneId = ? ORDER BY version DESC LIMIT 1""",
        (world_id, scene_id),
    )
    if not row:
        return None
    return json.loads(row["jsonBlob"])


def get_world_site_artifact(store: Any, world_id: str) -> dict[str, Any] | None:
    row = store.fetchone(
        """SELECT jsonBlob FROM MapArtifact
           WHERE worldId = ? AND sceneId IS NULL AND kind = 'site'
           ORDER BY version DESC LIMIT 1""",
        (world_id,),
    )
    if not row:
        return None
    return json.loads(row["jsonBlob"])


def put_artifact(
    store: Any,
    *,
    world_id: str,
    kind: str,
    payload: dict[str, Any],
    scene_id: str | None = None,
) -> str:
    aid = str(uuid.uuid4())
    store.run(
        """INSERT INTO MapArtifact
           (artifactId, worldId, sceneId, kind, version, jsonBlob, createdAt)
           VALUES (?, ?, ?, ?, 1, ?, ?)""",
        (aid, world_id, scene_id, kind, json.dumps(payload), ISO()),
    )
    store.commit()
    return aid
