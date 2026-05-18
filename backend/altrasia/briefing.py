from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


def set_briefing_fixture(
    store: SqlitePersistence,
    memory: Any,
    *,
    scene_id: str,
    fixture_key: str,
    text: str,
) -> dict[str, Any]:
    """Mirror briefing board text into scene fixture + world pool ([23] §4)."""
    scene = store.get_scene(scene_id)
    if not scene:
        raise ValueError("scene not found")
    cleaned = (text or "").strip()
    if not cleaned:
        raise ValueError("briefing text required")
    fixtures = SqlitePersistence.json_loads(scene.get("fixturesJson"), {})
    fixtures[fixture_key] = {
        "kind": "briefing",
        "label": fixture_key,
        "text": cleaned,
    }
    store.update_scene(scene_id, fixturesJson=json.dumps(fixtures), updatedAt=ISO())
    locus_key = f"briefing:{scene_id}:{fixture_key}"
    memory.memory_store(
        pool="world",
        owner_id=scene_id,
        locus_key=locus_key,
        value=cleaned[:8000],
    )
    return {"fixtureKey": fixture_key, "locusKey": locus_key, "sceneId": scene_id}
