"""Directed reply routing: one addressee + optional witness per operator line."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings

PROGRAM_OFFICE = "scene-program-office"


def _wait_jobs(
    client: TestClient,
    world_id: str,
    scene_id: str,
    *,
    min_done: int = 1,
    timeout: float = 60.0,
) -> None:
    store = client.app.state.services.store
    deadline = time.time() + timeout
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
def directed_client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "directed.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        client.patch(
            f"/api/v1/worlds/{world_id}",
            json={"activeSceneId": PROGRAM_OFFICE},
        )
        yield client, world_id


def test_directed_question_routes_to_addressee(directed_client: tuple) -> None:
    client, world_id = directed_client
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={
            "text": "Liam, what is your last name?",
            "scope": "public",
        },
    )
    assert resp.status_code == 200
    msg_id = resp.json()["messageId"]
    _wait_jobs(client, world_id, PROGRAM_OFFICE, min_done=1, timeout=60.0)

    store = client.app.state.services.store
    row = store.fetchone(
        "SELECT metaJson FROM Message WHERE messageId = ?",
        (msg_id,),
    )
    meta = json.loads(row["metaJson"])
    assert meta["orchestration"]["addressing"]["mode"] == "directed"
    assert meta["orchestration"]["addressing"]["primaryId"] == "char-liam-park"

    jobs = store.conn.execute(
        """SELECT characterId, continueDepth, trigger, triggerMessageId
           FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND status = 'done'
           ORDER BY createdAt""",
        (world_id, PROGRAM_OFFICE),
    ).fetchall()
    assert jobs
    first = jobs[0]
    assert first[2] == "persona_message"
    assert first[0] == "char-liam-park"
    assert first[3] == msg_id
    assert len(jobs) <= 2

    msgs = client.get(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages"
    ).json()
    finals = [
        m
        for m in msgs
        if m["role"] == "assistant" and m.get("streamStatus") == "final"
    ]
    assert 1 <= len(finals) <= 2
    assert finals[0]["characterId"] == "char-liam-park"
    speakers = [m["characterId"] for m in finals]
    assert len(speakers) == len(set(speakers))
    assert len(set(speakers)) <= 2


def test_directed_jobs_share_operator_trigger_message_id(directed_client: tuple) -> None:
    client, world_id = directed_client
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={"text": "Liam, quick check — last name?", "scope": "public"},
    )
    msg_id = resp.json()["messageId"]
    _wait_jobs(client, world_id, PROGRAM_OFFICE, min_done=1, timeout=60.0)

    store = client.app.state.services.store
    triggers = store.conn.execute(
        """SELECT DISTINCT triggerMessageId FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND status = 'done'""",
        (world_id, PROGRAM_OFFICE),
    ).fetchall()
    assert len(triggers) == 1
    assert triggers[0][0] == msg_id
