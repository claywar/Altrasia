"""MapDraft create + commit (MAP-AUTH-2)."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_layout_draft_commit(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "mapdraft.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    draft = client.post(
        f"/api/v1/worlds/{world_id}/layout-drafts",
        json={"brief": "Spread hall and kitchen apart", "scope": "mini"},
    ).json()
    assert draft["status"] == "ready"
    assert draft.get("proposed")
    did = draft["layoutDraftId"]

    deadline = time.time() + 8
    while time.time() < deadline:
        row = client.get(f"/api/v1/worlds/{world_id}/layout-drafts/{did}").json()
        if row["status"] == "ready":
            break
        time.sleep(0.05)

    commit = client.post(f"/api/v1/worlds/{world_id}/layout-drafts/{did}/commit").json()
    assert len(commit["applied"]) >= 1
    graph = client.get(f"/api/v1/worlds/{world_id}/spatial-graph").json()
    assert len(graph["nodes"]) >= 2
