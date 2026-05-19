"""World bootstrap draft + commit."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from tests.conftest import make_test_settings


def test_world_bootstrap_draft_commit(tmp_path: Path) -> None:
    with TestClient(create_app(make_test_settings(tmp_path, "bootstrap.db"))) as client:
        world = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
        wid = world["worldId"]
        active = world["activeSceneId"]

        draft = client.post(
            f"/api/v1/worlds/{wid}/layout-bootstrap-drafts",
            json={
                "description": "Add a rooftop terrace east of the lobby",
                "connectFromSceneId": active,
            },
        ).json()
        did = draft["layoutDraftId"]

        deadline = time.time() + 15
        row = draft
        while time.time() < deadline:
            row = client.get(f"/api/v1/worlds/{wid}/layout-drafts/{did}").json()
            if row["status"] == "ready":
                break
            time.sleep(0.05)
        assert row["status"] == "ready"

        commit = client.post(f"/api/v1/worlds/{wid}/layout-drafts/{did}/commit").json()
        assert commit.get("createdScenes")
        graph = client.get(f"/api/v1/worlds/{wid}/spatial-graph").json()
        assert any(n.get("position3d") for n in graph["nodes"])
