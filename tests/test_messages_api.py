"""Message list API: generationTrigger join for ambient idle lines."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.api.app import ISO


def test_list_messages_includes_generation_trigger_for_idle_job(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "msgs.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    w = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()
    world_id = w["worldId"]
    scene_id = w["activeSceneId"]
    chars = client.get(f"/api/v1/worlds/{world_id}/characters").json()
    cid = chars[0]["characterId"]
    job_id = "job-idle-test-1"
    msg_id = "msg-idle-test-1"
    svc = client.app.state.services  # type: ignore[attr-defined]
    svc.store.insert_job(
        {
            "jobId": job_id,
            "worldId": world_id,
            "characterId": cid,
            "sceneId": scene_id,
            "trigger": "idle_timer",
            "priority": 5,
            "observerMode": None,
            "status": "done",
            "continueDepth": 0,
            "triggerMessageId": None,
            "selectionRationaleJson": json.dumps(
                {"pick": "idle_timer", "characterId": cid, "idle_source": "tab_visible"}
            ),
            "createdAt": ISO(),
        }
    )
    svc.store.insert_message(
        {
            "messageId": msg_id,
            "worldId": world_id,
            "channelKind": "scene",
            "sceneId": scene_id,
            "role": "assistant",
            "characterId": cid,
            "outputText": "Ambient idle line.",
            "reasoning": None,
            "streamStatus": "final",
            "generationJobId": job_id,
            "metaJson": json.dumps({"communication": {"scope": "public"}}),
            "createdAt": ISO(),
        }
    )
    msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages").json()
    idle = next(m for m in msgs if m["messageId"] == msg_id)
    assert idle["generationTrigger"] == "idle_timer"
    assert idle["idleSource"] == "tab_visible"
    assert "jobRationaleJson" not in idle

    meta = json.loads(idle["metaJson"])
    meta.pop("orchestration", None)
    svc.store.update_message(msg_id, metaJson=json.dumps(meta))
    idle2 = next(
        m
        for m in client.get(f"/api/v1/worlds/{world_id}/scenes/{scene_id}/messages").json()
        if m["messageId"] == msg_id
    )
    assert idle2["generationTrigger"] == "idle_timer"
