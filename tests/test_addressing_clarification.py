"""Clarification turn when addressing is ambiguous."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.speaker_selection import parse_addressing

PRODUCT_STUDIO = "scene-product-studio"


def _wait_done(client: TestClient, world_id: str, scene_id: str, min_done: int = 1) -> None:
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


def test_ambiguous_first_name_triggers_clarification_mode() -> None:
    chars = {
        "char-dan-a": {
            "characterId": "char-dan-a",
            "displayName": "Dan Adams",
            "speechWeight": 0.5,
            "definitionJson": "{}",
        },
        "char-dan-b": {
            "characterId": "char-dan-b",
            "displayName": "Dan Brooks",
            "speechWeight": 0.6,
            "definitionJson": "{}",
        },
    }
    cast = ["char-dan-a", "char-dan-b"]
    result = parse_addressing("Dan, what is your role?", cast, chars)
    assert result.mode == "clarification"
    assert len(result.candidate_ids) == 2
    assert result.clarifier_id in result.candidate_ids


@pytest.fixture
def studio_client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "clarify.db",
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


def test_clarification_then_resolve_to_lena(studio_client: tuple) -> None:
    client, world_id = studio_client
    store = client.app.state.services.store
    cast = json.loads(store.get_scene(PRODUCT_STUDIO)["presentJson"])
    chars = {c["characterId"]: c for c in store.list_world_characters(world_id)}
    ambiguous = parse_addressing("Dan, what is your role?", cast, chars)
    if ambiguous.mode != "clarification":
        pytest.skip("no ambiguous Dan in product studio cast")

    resp1 = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PRODUCT_STUDIO}/messages",
        json={"text": "Dan, what is your role?", "scope": "public"},
    )
    msg1 = resp1.json()["messageId"]
    _wait_done(client, world_id, PRODUCT_STUDIO, min_done=1)

    jobs1 = store.conn.execute(
        """SELECT characterId, trigger FROM GenerationJob
           WHERE worldId = ? AND triggerMessageId = ? AND status = 'done'""",
        (world_id, msg1),
    ).fetchall()
    assert len(jobs1) == 1
    assert jobs1[0][0] == ambiguous.clarifier_id

    resp2 = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PRODUCT_STUDIO}/messages",
        json={"text": "Lena", "scope": "public"},
    )
    msg2 = resp2.json()["messageId"]
    _wait_done(client, world_id, PRODUCT_STUDIO, min_done=2)

    meta2 = json.loads(
        store.fetchone("SELECT metaJson FROM Message WHERE messageId = ?", (msg2,))[
            "metaJson"
        ]
    )
    assert meta2["orchestration"]["addressing"]["mode"] == "directed"
    assert meta2["orchestration"]["addressing"]["primaryId"] == "char-lena-cho"

    jobs2 = store.conn.execute(
        """SELECT characterId FROM GenerationJob
           WHERE worldId = ? AND triggerMessageId = ? AND status = 'done'""",
        (world_id, msg2),
    ).fetchall()
    assert any(row[0] == "char-lena-cho" for row in jobs2)
