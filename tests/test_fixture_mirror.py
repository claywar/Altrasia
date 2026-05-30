"""LP-4: fixture mirror to world loci."""

import json
from pathlib import Path

from altrasia.config import Settings
from altrasia.memory.fixture_sync import sync_scene_fixtures_to_loci
from altrasia.services import AppServices


def test_fixture_mirror_loci(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "mirror.db", mock_llm=True)
    svc = AppServices.create(settings)
    world_id = "w-mirror"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Mirror",
            "activeSceneId": "s1",
            "defaultModelProfile": "mock",
            "configJson": "{}",
            "worldMapJson": None,
            "eventSeq": 0,
            "createdAt": "2026-01-01T00:00:00+00:00",
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.insert_scene(
        {
            "sceneId": "s1",
            "worldId": world_id,
            "structureId": None,
            "mapLevel": 0,
            "levelLabel": None,
            "planPositionJson": None,
            "mapArtifactJson": None,
            "locationName": "Kitchen",
            "locationDescription": "Warm hearth",
            "presentJson": "[]",
            "fixturesJson": json.dumps(
                {
                    "kettle": {"label": "Kettle", "kind": "discrete", "portable": True},
                }
            ),
            "exitsJson": "[]",
            "activityJson": None,
            "roundRobinIndex": 0,
            "layoutHintsJson": None,
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    keys = sync_scene_fixtures_to_loci(svc.store, scene_id="s1")
    assert "location:s1:__scene__" in keys
    assert "location:s1:kettle" in keys
    row = svc.store.get_locus("world", "s1", "location:s1:kettle")
    assert row is not None
    assert "Kettle" in row["value"]
