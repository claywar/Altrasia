"""CTO briefing assembly: summon tools move cast to conference room."""

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.presence import PresenceService


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    db = tmp_path / "summon.db"
    settings = Settings(
        data_dir=db.parent,
        db_path=db,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc, tc.app.state.services


def _wait_jobs(client: TestClient, world_id: str, services: object, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        row = services.store.conn.execute(
            """SELECT COUNT(*) FROM GenerationJob
               WHERE worldId = ? AND status IN ('queued', 'running')""",
            (world_id,),
        ).fetchone()
        if row[0] == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_cto_briefing_summons_directors_to_conference(client: tuple[TestClient, object]) -> None:
    tc, svc = client
    world_id = tc.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()["worldId"]
    lobby = "scene-lobby"
    conference = "scene-conference-room"

    tc.post(
        f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages",
        json={
            "text": (
                "Call the members into your conference room so I may observe "
                "your briefing and their thoughts. I will meet you there."
            ),
            "scope": "public",
        },
    )
    _wait_jobs(tc, world_id, svc)

    scene = svc.store.get_scene(conference)
    present = PresenceService.parse_present(scene["presentJson"])
    assert "char-sofia-mendez" in present
    assert "char-liam-park" in present

    msgs = tc.get(f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages").json()
    assistant = next(m for m in msgs if m["role"] == "assistant")
    text = assistant["outputText"].lower()
    assert "sofia" in text or "mendez" in text
    assert "sarah" not in text
    assert "david" not in text

    jobs = svc.store.fetchall(
        """SELECT trigger, selectionRationaleJson FROM GenerationJob
           WHERE worldId = ? ORDER BY createdAt""",
        (world_id,),
    )
    rationales = [j["selectionRationaleJson"] for j in jobs if j["selectionRationaleJson"]]
    assert any("scene_summon" in r for r in rationales)

    import json

    announce = [
        m
        for m in msgs
        if json.loads(m["metaJson"]).get("orchestration", {}).get("kind")
        == "presence_announce"
    ]
    assert announce
    joined = " ".join(m["outputText"] for m in announce).lower()
    assert "sofia" in joined or "mendez" in joined
    assert "assistance" in joined or "join" in joined
