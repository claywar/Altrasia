"""Unified layout draft API (server-side mini→site→stack cascade)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_unified_layout_draft_create_and_commit(tmp_path: Path) -> None:
    settings = Settings(
        data_dir=tmp_path,
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
        json={"brief": "Arrange lobby and conference room with site envelope"},
    ).json()
    did = draft["layoutDraftId"]

    import time

    deadline = time.time() + 30
    row = draft
    while time.time() < deadline:
        row = client.get(f"/api/v1/worlds/{world_id}/layout-drafts/{did}").json()
        if row["status"] == "ready":
            break
        time.sleep(0.1)
    assert row["status"] == "ready"
    assert row.get("proposed")
    assert row.get("scope") == "unified"

    commit = client.post(f"/api/v1/worlds/{world_id}/layout-drafts/{did}/commit").json()
    assert len(commit["applied"]) >= 1
