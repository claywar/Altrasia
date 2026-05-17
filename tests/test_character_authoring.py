"""Phase 3 character authoring API (CHAR-1–CHAR-5)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = Settings(
        db_path=tmp_path / "char.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    return TestClient(create_app(settings))


def test_character_draft_and_approve(client: TestClient) -> None:
    world = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    world_id = world["worldId"]

    draft = client.post(
        "/api/v1/characters/draft",
        json={"brief": "A shy librarian who speaks in metaphors."},
    )
    assert draft.status_code == 200
    body = draft.json()
    assert body["status"] == "ready"
    assert body["definitionJson"]["persona"]
    assert body["definitionJson"]["instructions"]
    draft_id = body["draftId"]

    # CHAR-2: roster grows only after approve
    chars_before = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    count_before = len(chars_before.get("atLocation", [])) + len(
        chars_before.get("elsewhere", [])
    )

    created = client.post(
        "/api/v1/characters",
        json={
            "draftId": draft_id,
            "worldId": world_id,
            "displayName": "Librarian",
        },
    )
    assert created.status_code == 200
    char_id = created.json()["characterId"]
    assert char_id.startswith("char-")

    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    all_ids = {c["characterId"] for c in roster.get("atLocation", [])} | {
        c["characterId"] for c in roster.get("elsewhere", [])
    }
    assert char_id in all_ids
    assert len(all_ids) >= count_before + 1

    poll = client.get(f"/api/v1/characters/draft/{draft_id}").json()
    assert poll["status"] == "approved"


def test_discard_character_draft(client: TestClient) -> None:
    draft = client.post(
        "/api/v1/characters/draft",
        json={"brief": "A guard at the gate."},
    ).json()
    r = client.delete(f"/api/v1/characters/draft/{draft['draftId']}")
    assert r.status_code == 200
    assert r.json()["status"] == "discarded"


def test_add_world_member_endpoint(client: TestClient) -> None:
    world_id = client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    draft = client.post(
        "/api/v1/characters/draft",
        json={"brief": "A traveling merchant."},
    ).json()
    created = client.post(
        "/api/v1/characters",
        json={"draftId": draft["draftId"], "displayName": "Merchant"},
    ).json()
    char_id = created["characterId"]

    r = client.post(
        f"/api/v1/worlds/{world_id}/members",
        json={"characterId": char_id},
    )
    assert r.status_code == 200
    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    all_ids = {c["characterId"] for c in roster.get("atLocation", [])} | {
        c["characterId"] for c in roster.get("elsewhere", [])
    }
    assert char_id in all_ids
