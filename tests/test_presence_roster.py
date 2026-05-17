"""Roster unplaced cast + summon to active scene."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_unplaced_roster_and_summon(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "presence.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    hall = "scene-hall"

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
