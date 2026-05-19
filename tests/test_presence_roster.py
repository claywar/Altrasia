"""Roster unplaced cast + summon to active scene."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_unplaced_roster_and_summon(tmp_path: Path) -> None:
    from tests.conftest import make_test_settings

    with TestClient(create_app(make_test_settings(tmp_path, "presence.db"))) as client:
        _run_presence_roster(client)


def _run_presence_roster(client: TestClient) -> None:
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall = "scene-lobby"

    draft = client.post(
        "/api/v1/characters/draft",
        json={"brief": "A quiet herbalist."},
    ).json()
    created = client.post(
        "/api/v1/characters",
        json={"draftId": draft["draftId"], "worldId": world_id, "displayName": "Herbalist"},
    ).json()
    char_id = created["characterId"]

    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    assert any(u["characterId"] == char_id for u in roster["unplaced"])

    r = client.post(
        f"/api/v1/worlds/{world_id}/presence/summon",
        json={"characterIds": [char_id], "targetSceneId": hall},
    )
    assert r.status_code == 200

    roster2 = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    assert any(p["characterId"] == char_id for p in roster2["atLocation"])
    assert not any(u["characterId"] == char_id for u in roster2["unplaced"])

    kitchen = "scene-conference-room"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": char_id},
    )
    roster3 = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    assert any(
        p["characterId"] == char_id and p.get("sceneId") == kitchen
        for p in roster3["elsewhere"]
    )
