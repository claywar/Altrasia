"""Unified layout draft API (server-side mini→site→stack cascade)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_unified_layout_draft_create_and_commit(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "unified.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    draft = client.post(
        f"/api/v1/worlds/{world_id}/layout-drafts/unified",
        json={"brief": "Arrange hall and kitchen with site envelope"},
    ).json()
    assert draft["status"] == "ready"
    assert draft.get("proposed")
    assert draft.get("scope") == "unified"
    did = draft["layoutDraftId"]

    commit = client.post(f"/api/v1/worlds/{world_id}/layout-drafts/{did}/commit").json()
    assert len(commit["applied"]) >= 1
