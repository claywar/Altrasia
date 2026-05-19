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
LOBBY = "scene-lobby"


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


def test_nickname_directed_only_addressee_replies(directed_client: tuple) -> None:
    """Fuzzy nickname to one addressee must not summon unmentioned witnesses."""
    client, world_id = directed_client
    client.patch(f"/api/v1/worlds/{world_id}", json={"activeSceneId": LOBBY})
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{LOBBY}/presence/join",
        json={"characterId": "char-sofia-mendez"},
    )
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{LOBBY}/messages",
        json={"text": "Jordie, what is your role?", "scope": "public"},
    )
    assert resp.status_code == 200
    msg_id = resp.json()["messageId"]
    _wait_jobs(client, world_id, LOBBY, min_done=1, timeout=60.0)

    store = client.app.state.services.store
    meta = json.loads(
        store.fetchone("SELECT metaJson FROM Message WHERE messageId = ?", (msg_id,))[
            "metaJson"
        ]
    )
    assert meta["orchestration"]["addressing"]["mode"] == "directed"
    assert meta["orchestration"]["addressing"]["primaryId"] == "char-jordan-reyes"

    jobs = store.conn.execute(
        """SELECT characterId, continueDepth, trigger FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ? AND status = 'done'
           ORDER BY createdAt""",
        (world_id, LOBBY, msg_id),
    ).fetchall()
    assert len(jobs) == 1
    assert jobs[0][0] == "char-jordan-reyes"
    assert jobs[0][2] == "persona_message"

    msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{LOBBY}/messages").json()
    finals = [
        m
        for m in msgs
        if m["role"] == "assistant" and m.get("streamStatus") == "final"
    ]
    assert len(finals) == 1
    assert finals[0]["characterId"] == "char-jordan-reyes"


def test_partial_multi_only_present_addressees_reply(directed_client: tuple) -> None:
    """Lili absent, Rach present — only Rachel speaks, not open pile-on."""
    client, world_id = directed_client
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages",
        json={"text": "Lili, Rach, what do you do here?", "scope": "public"},
    )
    assert resp.status_code == 200
    msg_id = resp.json()["messageId"]
    _wait_jobs(client, world_id, PROGRAM_OFFICE, min_done=1, timeout=60.0)

    store = client.app.state.services.store
    meta = json.loads(
        store.fetchone("SELECT metaJson FROM Message WHERE messageId = ?", (msg_id,))[
            "metaJson"
        ]
    )
    assert meta["orchestration"]["addressing"]["mode"] == "directed"
    assert meta["orchestration"]["addressing"]["addresseeIds"] == ["char-rachel-kim"]

    jobs = store.conn.execute(
        """SELECT characterId, trigger FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? AND triggerMessageId = ? AND status = 'done'""",
        (world_id, PROGRAM_OFFICE, msg_id),
    ).fetchall()
    assert len(jobs) == 1
    assert jobs[0][0] == "char-rachel-kim"

    msgs = client.get(
        f"/api/v1/worlds/{world_id}/scenes/{PROGRAM_OFFICE}/messages"
    ).json()
    finals = [
        m
        for m in msgs
        if m["role"] == "assistant" and m.get("streamStatus") == "final"
    ]
    assert len(finals) == 1
    assert finals[0]["characterId"] == "char-rachel-kim"


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
