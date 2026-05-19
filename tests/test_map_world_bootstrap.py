"""World bootstrap draft + commit."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def test_world_bootstrap_draft_commit(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "bootstrap.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    wid = world["worldId"]
    active = world["activeSceneId"]

    draft = client.post(
        f"/api/v1/worlds/{wid}/layout-bootstrap-drafts",
        json={"description": "Add a walled garden east of the hall", "connectFromSceneId": active},
    ).json()
    assert draft["status"] == "ready"
    did = draft["layoutDraftId"]

    commit = client.post(f"/api/v1/worlds/{wid}/layout-drafts/{did}/commit").json()
    assert commit.get("createdScenes")
    graph = client.get(f"/api/v1/worlds/{wid}/spatial-graph").json()
    assert any(n.get("position3d") for n in graph["nodes"])
