"""Narrative presence auto pickup."""

import json
from pathlib import Path

import pytest

from altrasia.config import Settings
from altrasia.domain.inventory import get_member_inventory
from altrasia.domain.narrative_presence import apply_narrative_presence, detect_narrative_presence
from altrasia.services import AppServices


@pytest.mark.asyncio
async def test_narrative_pickup_auto(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "narr.db", mock_llm=True)
    svc = AppServices.create(settings)
    world_id = "w-narr"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Narr",
            "activeSceneId": "s1",
            "defaultModelProfile": "mock",
            "configJson": json.dumps({"narrativePresenceMode": "auto"}),
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
            "locationName": "Room",
            "locationDescription": "",
            "presentJson": '["c1"]',
            "fixturesJson": json.dumps(
                {
                    "mug": {
                        "label": "Travel mug",
                        "kind": "discrete",
                        "portable": True,
                    }
                }
            ),
            "exitsJson": "[]",
            "activityJson": None,
            "roundRobinIndex": 0,
            "layoutHintsJson": None,
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.insert_character(
        {
            "characterId": "c1",
            "displayName": "Alice",
            "definitionJson": "{}",
            "modelProfile": "mock",
            "speechWeight": 0.5,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.add_world_member(world_id, "c1")
    cfg = json.loads(svc.store.get_world(world_id)["configJson"])
    detection = detect_narrative_presence(
        svc,
        world_id=world_id,
        speaker_id="c1",
        scene_id="s1",
        output_text="Alice picks up the Travel mug and examines it.",
        cfg=cfg,
    )
    assert detection is not None
    assert any(a["kind"] == "pickup" for a in detection["actions"])
    await apply_narrative_presence(
        svc,
        world_id=world_id,
        detection=detection,
        speaker_id="c1",
        source_scene_id="s1",
    )
    scene = svc.store.get_scene("s1")
    fixtures = json.loads(scene["fixturesJson"])
    assert "mug" not in fixtures
    inv = get_member_inventory(svc.store, world_id, "c1")
    assert any(i["label"] == "Travel mug" for i in inv["held"])
