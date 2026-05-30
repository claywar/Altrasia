"""Scene shared stashes (GS-1–5)."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.inventory import get_member_inventory
from altrasia.domain.shared_stash import (
    deposit_to_stash,
    format_stash_summary,
    get_scene_stash,
    take_from_stash,
)
from altrasia.fixtures.loader import load_fixture_by_id
from altrasia.prompt.scene_framing import build_scene_framing
from altrasia.services import AppServices


def _client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        db_path=tmp_path / "stash.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    return client, world_id


def test_break_room_stash_in_fixture(tmp_path: Path) -> None:
    client, _world_id = _client(tmp_path)
    store = client.app.state.services.store  # type: ignore[attr-defined]
    stash = get_scene_stash(store, "scene-break-room")
    assert "snack-shelf" in stash
    assert len(stash["snack-shelf"]["items"]) >= 2
    summary = format_stash_summary(stash)
    assert "Snack shelf" in summary


def test_stash_take_and_deposit(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    cid = "char-jordan-reyes"
    scene_id = "scene-break-room"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/join",
        json={"characterId": cid},
    )
    store = client.app.state.services.store  # type: ignore[attr-defined]
    before = len(get_scene_stash(store, scene_id)["snack-shelf"]["items"])
    out = take_from_stash(
        store,
        world_id=world_id,
        scene_id=scene_id,
        character_id=cid,
        stash_key="snack-shelf",
        item_id="item-granola-1",
    )
    assert out["itemId"] == "item-granola-1"
    after = len(get_scene_stash(store, scene_id)["snack-shelf"]["items"])
    assert after == before - 1
    inv = get_member_inventory(store, world_id, cid)
    assert any(i.get("itemId") == "item-granola-1" for i in inv["held"])
    deposit_to_stash(
        store,
        world_id=world_id,
        scene_id=scene_id,
        character_id=cid,
        stash_key="snack-shelf",
        item_id="item-granola-1",
    )
    assert len(get_scene_stash(store, scene_id)["snack-shelf"]["items"]) == before


def test_stash_take_first_item_without_id(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    cid = "char-jordan-reyes"
    scene_id = "scene-break-room"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/presence/join",
        json={"characterId": cid},
    )
    store = client.app.state.services.store  # type: ignore[attr-defined]
    out = take_from_stash(
        store,
        world_id=world_id,
        scene_id=scene_id,
        character_id=cid,
        stash_key="snack-shelf",
    )
    assert out.get("itemId")


def test_stash_framing_line(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "frame.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    svc = AppServices.create(settings)
    meta = load_fixture_by_id(svc.store, settings.fixtures_dir, "demo-spatial-v1")
    world_id = meta["worldId"]
    framing = build_scene_framing(
        svc.store,
        svc.presence,
        world_id=world_id,
        character_id="char-jordan-reyes",
        scene_id="scene-break-room",
    )
    assert "Shared:" in framing
    assert "Snack shelf" in framing


def test_patch_scene_shared_stash_json(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    scene_id = "scene-break-room"
    payload = {
        "snack-shelf": {
            "label": "Snack shelf",
            "items": [{"itemId": "item-x", "label": "apple"}],
            "capacity": 5,
        }
    }
    out = client.patch(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}",
        json={"sharedStashJson": json.dumps(payload)},
    ).json()
    assert "snack-shelf" in out.get("sharedStashJson", "")
