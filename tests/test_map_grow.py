"""MAP-GROW: add connected scenes after geography lock."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_map_grow_after_lock(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "grow.db", mock_llm=True)
    client = TestClient(create_app(settings))
    world = client.post("/api/v1/worlds", json={"name": "Grow Test"}).json()
    world_id = world["worldId"]
    start = world["activeSceneId"]

    client.post(f"/api/v1/worlds/{world_id}/geography/lock")

    blocked = client.post(
        f"/api/v1/worlds/{world_id}/scenes",
        json={"locationName": "Orphan Room"},
    )
    assert blocked.status_code == 403

    attic = client.post(
        f"/api/v1/worlds/{world_id}/scenes",
        json={
            "locationName": "Attic",
            "connectFromSceneId": start,
            "exitLabel": "Stairs up",
        },
    )
    assert attic.status_code == 200
    attic_id = attic.json()["sceneId"]

    rename = client.patch(
        f"/api/v1/worlds/{world_id}/scenes/{attic_id}",
        json={"locationName": "Old Attic"},
    )
    assert rename.status_code == 200
    assert rename.json()["locationName"] == "Old Attic"

    chars = client.get(f"/api/v1/worlds/{world_id}/characters").json()
    assert isinstance(chars, list)
