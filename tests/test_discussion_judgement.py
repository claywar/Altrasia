"""Discussion judgement: character signals + orchestrator assessment."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.orchestrator.discussion_judgement import (
    apply_tool_log_signals,
    assess_discussion_continuation,
    get_ensemble_discussion,
    record_character_signal,
)


@pytest.fixture
def svc_bundle(tmp_path: Path):
    settings = Settings(
        data_dir=tmp_path,
        db_path=tmp_path / "judge.db",
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
            json={"activeSceneId": "scene-program-office"},
        )
        svc = client.app.state.services
        yield svc, world_id, client


def test_character_signal_extends_unresolved(svc_bundle: tuple) -> None:
    svc, world_id, client = svc_bundle
    scene_id = "scene-program-office"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages",
        json={
            "text": "Everyone discuss program management — align on how we run intake.",
            "scope": "public",
        },
    )
    record_character_signal(
        svc.store,
        scene_id,
        "char-nina-patel",
        sufficient=False,
        gaps=["vendor SLAs", "risk owners"],
        note="Critical dependencies not named yet.",
    )
    cfg = json.loads(svc.store.get_world(world_id)["configJson"])
    unresolved, reason, detail = asyncio.run(
        assess_discussion_continuation(
            svc,
            world_id=world_id,
            scene_id=scene_id,
            cfg=cfg,
            current_depth=8,
        )
    )
    assert unresolved
    assert reason == "character_reported_gaps"
    assert detail["mode"] == "character_signals"
    ensemble = get_ensemble_discussion(svc.store.get_scene(scene_id))
    assert ensemble and len(ensemble.get("signals") or []) == 1


def test_tool_log_records_discussion_signal(svc_bundle: tuple) -> None:
    svc, world_id, _client = svc_bundle
    scene_id = "scene-program-office"
    n = apply_tool_log_signals(
        svc.store,
        scene_id,
        "char-tom-bradley",
        [
            {
                "name": "discussion_signal",
                "arguments": {
                    "sufficient": False,
                    "gaps": ["critical path visibility"],
                    "note": "Need clearer owners",
                },
            }
        ],
        message_id="msg-1",
    )
    assert n == 1
    ensemble = get_ensemble_discussion(svc.store.get_scene(scene_id))
    assert ensemble
    assert ensemble["signals"][0]["characterId"] == "char-tom-bradley"
    assert ensemble["signals"][0]["gaps"] == ["critical path visibility"]
