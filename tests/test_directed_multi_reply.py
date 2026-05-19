"""Multi-addressee directed replies: each named character speaks in turn."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings

PRODUCT_STUDIO = "scene-product-studio"


def _wait_done(client: TestClient, world_id: str, scene_id: str, min_done: int = 2) -> None:
    store = client.app.state.services.store
    deadline = time.time() + 60.0
    while time.time() < deadline:
        pending = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status IN ('queued', 'running')""",
            (world_id, scene_id),
        ).fetchone()[0]
        done = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status = 'done'""",
            (world_id, scene_id),
        ).fetchone()[0]
        if pending == 0 and done >= min_done:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


@pytest.fixture
def studio_client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "multi.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    with TestClient(create_app(settings)) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        client.patch(
            f"/api/v1/worlds/{world_id}",
            json={"activeSceneId": PRODUCT_STUDIO},
        )
        yield client, world_id


def test_marco_and_lena_both_reply(studio_client: tuple) -> None:
    client, world_id = studio_client
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PRODUCT_STUDIO}/messages",
        json={"text": "Marco and Lena, what are your roles?", "scope": "public"},
    )
    assert resp.status_code == 200
    msg_id = resp.json()["messageId"]
    _wait_done(client, world_id, PRODUCT_STUDIO, min_done=2)

    store = client.app.state.services.store
    meta = json.loads(
        store.fetchone(
            "SELECT metaJson FROM Message WHERE messageId = ?",
            (msg_id,),
        )["metaJson"]
    )
    assert meta["orchestration"]["addressing"]["addresseeIds"] == [
        "char-marco-delgado",
        "char-lena-cho",
    ]

    done_chars = [
        row[0]
        for row in store.conn.execute(
            """SELECT characterId FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ?
                 AND status = 'done' ORDER BY createdAt""",
            (world_id, PRODUCT_STUDIO, msg_id),
        ).fetchall()
    ]
    assert "char-marco-delgado" in done_chars
    assert "char-lena-cho" in done_chars
    assert len(done_chars) == 2
