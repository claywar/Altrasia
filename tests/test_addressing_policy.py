"""Generic addressing policy gates all scene generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.addressing_policy import (
    may_character_generate,
    scene_has_unanswered_directed,
)
from altrasia.orchestrator.speaker_selection import addressing_to_dict, parse_addressing

PRODUCT_STUDIO = "scene-product-studio"


@pytest.fixture
def studio_client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "policy.db",
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


def test_andre_directed_parsing(studio_client: tuple) -> None:
    client, world_id = studio_client
    store = client.app.state.services.store
    cast = json.loads(store.get_scene(PRODUCT_STUDIO)["presentJson"])
    chars = {c["characterId"]: c for c in store.list_world_characters(world_id)}
    text = "Andre, what is your last name and who do you report to?"
    result = parse_addressing(text, cast, chars)
    assert result.mode == "directed"
    assert result.primary_id == "char-andre-silva"


def test_may_character_generate_blocks_idle_and_wrong_speaker(
    studio_client: tuple,
) -> None:
    client, world_id = studio_client
    svc = client.app.state.services
    store = svc.store
    cast = json.loads(store.get_scene(PRODUCT_STUDIO)["presentJson"])
    chars = {c["characterId"]: c for c in store.list_world_characters(world_id)}
    text = "Andre, what is your last name and who do you report to?"
    addressing = parse_addressing(text, cast, chars)
    msg_id = "op-andre-1"
    store.insert_message(
        {
            "messageId": msg_id,
            "worldId": world_id,
            "channelKind": "scene",
            "sceneId": PRODUCT_STUDIO,
            "role": "user",
            "characterId": None,
            "outputText": text,
            "reasoning": None,
            "streamStatus": "final",
            "generationJobId": None,
            "metaJson": json.dumps(
                {"orchestration": {"addressing": addressing_to_dict(addressing)}}
            ),
            "createdAt": "2026-01-01T00:00:00+00:00",
        }
    )
    cfg = svc.orchestrator._world_config(world_id)
    idle_job = {
        "worldId": world_id,
        "sceneId": PRODUCT_STUDIO,
        "characterId": "char-hannah-brooks",
        "trigger": "idle_timer",
        "continueDepth": 0,
        "triggerMessageId": None,
    }
    allowed, reason = may_character_generate(svc, idle_job, cfg)
    assert not allowed
    assert reason == "directed_blocks_idle"

    wrong = {
        **idle_job,
        "trigger": "persona_message",
        "triggerMessageId": msg_id,
        "characterId": "char-hannah-brooks",
    }
    allowed2, reason2 = may_character_generate(svc, wrong, cfg)
    assert not allowed2
    assert reason2 == "directed_wrong_speaker_at_depth_0"

    primary = {
        **wrong,
        "characterId": "char-andre-silva",
    }
    allowed3, _ = may_character_generate(svc, primary, cfg)
    assert allowed3

    assert scene_has_unanswered_directed(store, world_id, PRODUCT_STUDIO)


def test_product_studio_andre_integration(studio_client: tuple) -> None:
    import time

    client, world_id = studio_client
    resp = client.post(
        f"/api/v1/worlds/{world_id}/scenes/{PRODUCT_STUDIO}/messages",
        json={
            "text": "Andre, what is your last name and who do you report to?",
            "scope": "public",
        },
    )
    assert resp.status_code == 200
    msg_id = resp.json()["messageId"]
    store = client.app.state.services.store
    deadline = time.time() + 60.0
    while time.time() < deadline:
        pending = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status IN ('queued', 'running')""",
            (world_id, PRODUCT_STUDIO),
        ).fetchone()[0]
        done = store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND sceneId = ? AND status = 'done'""",
            (world_id, PRODUCT_STUDIO),
        ).fetchone()[0]
        if pending == 0 and done >= 1:
            break
        time.sleep(0.1)
    else:
        pytest.fail("generation did not finish")

    jobs = store.conn.execute(
        """SELECT characterId, trigger, status, selectionRationaleJson
           FROM GenerationJob WHERE worldId = ? AND sceneId = ?""",
        (world_id, PRODUCT_STUDIO),
    ).fetchall()
    done_jobs = [j for j in jobs if j[2] == "done"]
    cancelled = [j for j in jobs if j[2] == "cancelled"]
    assert done_jobs
    assert all(j[0] == "char-andre-silva" for j in done_jobs), done_jobs
    assert len(done_jobs) <= 2
    for j in cancelled:
        rationale = json.loads(j[3] or "{}")
        assert rationale.get("suppressed") or j[0] != "char-andre-silva"

    first_job = store.conn.execute(
        """SELECT characterId FROM GenerationJob
           WHERE worldId = ? AND triggerMessageId = ? AND trigger = 'persona_message'""",
        (world_id, msg_id),
    ).fetchone()
    assert first_job[0] == "char-andre-silva"
