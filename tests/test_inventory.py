"""Character inventory persistence and domain (LP-2)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.inventory import (
    format_inventory_summary,
    get_member_inventory,
    give_item,
    pickup_fixture,
    set_member_inventory,
)


def _client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        db_path=tmp_path / "inv.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    return client, world_id


def test_inventory_api_and_world_scoped_across_scenes(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    cid = "char-jordan-reyes"
    inv = client.get(f"/api/v1/worlds/{world_id}/characters/{cid}/inventory").json()
    assert inv["inventory"]["worn"]
    assert inv["inventory"]["held"]

    patched = {
        "worn": [{"itemId": "item-test", "label": "test apron", "wearable": True}],
        "held": [],
        "containers": [],
    }
    out = client.patch(
        f"/api/v1/worlds/{world_id}/characters/{cid}/inventory",
        json={"inventory": patched},
    ).json()
    assert out["inventory"]["worn"][0]["label"] == "test apron"

    scenes = client.get(f"/api/v1/worlds/{world_id}/scenes").json()
    target = next(s for s in scenes if s["sceneId"] != scenes[0]["sceneId"])
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{target['sceneId']}/presence/join",
        json={"characterId": cid},
    )
    again = client.get(f"/api/v1/worlds/{world_id}/characters/{cid}/inventory").json()
    assert again["inventory"]["worn"][0]["label"] == "test apron"


def test_list_characters_includes_inventory_summary(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    chars = client.get(f"/api/v1/worlds/{world_id}/characters").json()
    jordan = next(c for c in chars if c["characterId"] == "char-jordan-reyes")
    assert "inventorySummary" in jordan
    assert "blazer" in jordan["inventorySummary"] or "tablet" in jordan["inventorySummary"]


def test_container_capacity(tmp_path: Path) -> None:
    from altrasia.domain.inventory import move_item
    from altrasia.services import AppServices

    settings = Settings(db_path=tmp_path / "cap.db", mock_llm=True)
    svc = AppServices.create(settings)
    world_id = "w-cap"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Cap",
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
            "locationName": "Room",
            "locationDescription": "",
            "presentJson": "[]",
            "fixturesJson": "{}",
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
            "displayName": "A",
            "definitionJson": "{}",
            "modelProfile": "mock",
            "speechWeight": 0.5,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.add_world_member(world_id, "c1")
    inv = {
        "worn": [],
        "held": [{"itemId": "h1", "label": "key"}],
        "containers": [
            {"itemId": "bag1", "label": "bag", "containerCapacity": 1, "contents": []}
        ],
    }
    set_member_inventory(svc.store, world_id, "c1", inv)
    move_item(
        svc.store,
        world_id=world_id,
        character_id="c1",
        item_id="h1",
        to_slot="container",
        container_item_id="bag1",
    )
    loaded = get_member_inventory(svc.store, world_id, "c1")
    assert loaded["containers"][0]["contents"][0]["itemId"] == "h1"


def test_give_item_between_characters(tmp_path: Path) -> None:
    from altrasia.services import AppServices

    settings = Settings(db_path=tmp_path / "give.db", mock_llm=True)
    svc = AppServices.create(settings)
    world_id = "w-give"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Give",
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
            "locationName": "Room",
            "locationDescription": "",
            "presentJson": '["c1","c2"]',
            "fixturesJson": "{}",
            "exitsJson": "[]",
            "activityJson": None,
            "roundRobinIndex": 0,
            "layoutHintsJson": None,
            "updatedAt": "2026-01-01T00:00:00+00:00",
        }
    )
    for cid, name in (("c1", "Alice"), ("c2", "Bob")):
        svc.store.insert_character(
            {
                "characterId": cid,
                "displayName": name,
                "definitionJson": "{}",
                "modelProfile": "mock",
                "speechWeight": 0.5,
                "createdAt": "2026-01-01T00:00:00+00:00",
            }
        )
        svc.store.add_world_member(world_id, cid)
    set_member_inventory(
        svc.store,
        world_id,
        "c1",
        {"worn": [], "held": [{"itemId": "i1", "label": "mug"}], "containers": []},
    )
    give_item(
        svc.store,
        world_id=world_id,
        from_character_id="c1",
        to_character_id="c2",
        item_id="i1",
    )
    assert not get_member_inventory(svc.store, world_id, "c1")["held"]
    assert get_member_inventory(svc.store, world_id, "c2")["held"][0]["label"] == "mug"


def test_pickup_fixture_removes_from_scene(tmp_path: Path) -> None:
    import json

    from altrasia.services import AppServices

    settings = Settings(db_path=tmp_path / "pick.db", mock_llm=True)
    svc = AppServices.create(settings)
    world_id = "w-pick"
    svc.store.insert_world(
        {
            "worldId": world_id,
            "name": "Pick",
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
            "displayName": "A",
            "definitionJson": "{}",
            "modelProfile": "mock",
            "speechWeight": 0.5,
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    svc.store.add_world_member(world_id, "c1")
    pickup_fixture(
        svc.store,
        world_id=world_id,
        scene_id="s1",
        character_id="c1",
        fixture_key="mug",
    )
    scene = svc.store.get_scene("s1")
    fixtures = json.loads(scene["fixturesJson"])
    assert "mug" not in fixtures
    inv = get_member_inventory(svc.store, world_id, "c1")
    assert any(i["label"] == "Travel mug" for i in inv["held"])
    summary = format_inventory_summary(inv)
    assert "Travel mug" in summary
