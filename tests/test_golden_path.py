"""Spatial golden path (docs/17-acceptance-criteria.md §2) — integration with mock LLM."""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.inference.profiles import quality_addendum


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, Path, object]:
    db = tmp_path / "golden.db"
    settings = Settings(
        data_dir=db.parent,
        db_path=db,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    with TestClient(app) as tc:
        yield tc, db, tc.app.state.services


def _wait_jobs(
    client: TestClient,
    world_id: str,
    timeout: float = 30.0,
    services: object | None = None,
) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if services is not None:
            row = services.store.conn.execute(
                """SELECT COUNT(*) FROM GenerationJob
                   WHERE worldId = ? AND status IN ('queued', 'running')""",
                (world_id,),
            ).fetchone()
            if row[0] == 0:
                return
        else:
            q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
            if not q.get("busy") and q.get("depth", 0) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_golden_path_spatial(client: tuple[TestClient, Path, object]) -> None:
    client, db_path, services = client
    # GP-SETUP
    r = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"})
    assert r.status_code == 200
    world_id = r.json()["worldId"]
    lobby = "scene-lobby"
    conference = "scene-conference-room"

    # Step 1: world has 2 scenes and cast
    scenes = client.get(f"/api/v1/worlds/{world_id}/scenes").json()
    assert len(scenes) >= 2

    # Step 2: public line → NPC reply
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages",
        json={"text": "Hello Jordan?", "scope": "public"},
    )
    _wait_jobs(client, world_id, services=services)
    msgs = client.get(f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages").json()
    assert any(m["role"] == "assistant" for m in msgs)

    # Step 3: move persona to conference room; elsewhere roster
    client.patch(f"/api/v1/worlds/{world_id}", json={"activeSceneId": conference})
    roster = client.get(f"/api/v1/worlds/{world_id}/roster").json()
    elsewhere = {e["characterId"] for e in roster["elsewhere"]}
    assert "char-jordan-reyes" in elsewhere

    # Step 4: knock — signal pending, no generation enqueued (CC-11a)
    depth_before = client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"]
    client.post(
        f"/api/v1/worlds/{world_id}/signals",
        json={"kind": "knock", "sourceSceneId": conference, "targetSceneId": lobby},
    )
    sigs = client.get(f"/api/v1/worlds/{world_id}/signals").json()
    assert any(s["status"] == "pending" for s in sigs)
    depth_after = client.get(f"/api/v1/worlds/{world_id}/queue").json()["depth"]
    assert depth_after == depth_before

    # Step 5: Observer meta-chat
    client.post(
        f"/api/v1/worlds/{world_id}/observer/meta-messages",
        json={"text": "Rename lobby fixture reception to main reception"},
    )
    meta = client.get(f"/api/v1/worlds/{world_id}/observer/meta-messages").json()
    assert len(meta) >= 2

    # Step 6: restart hydration — new client, same DB
    settings = Settings(
        data_dir=db_path.parent,
        db_path=db_path,
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    with TestClient(create_app(settings)) as client2:
        w2 = client2.get(f"/api/v1/worlds/{world_id}").json()
        assert w2["activeSceneId"] == conference
        sigs2 = client2.get(f"/api/v1/worlds/{world_id}/signals").json()
        assert any(s["status"] == "pending" for s in sigs2)

    # Step 7: group scene — Sofia joins lobby; diary fan-out (MP-20)
    client.patch(f"/api/v1/worlds/{world_id}", json={"activeSceneId": lobby})
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{lobby}/presence/join",
        json={"characterId": "char-sofia-mendez"},
    )
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages",
        json={"text": "Good evening both of you.", "scope": "public"},
    )
    _wait_jobs(client, world_id, timeout=45.0, services=services)
    sofia_diary = client.get(
        f"/api/v1/worlds/{world_id}/characters/char-sofia-mendez/diary"
    ).json()
    assert len(sofia_diary) >= 1
    assert any("evening" in seg["text"].lower() for seg in sofia_diary)

    # Step 8: agent_continue chain — Sofia then Jordan (AO-19)
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{lobby}/messages",
        json={"text": "Sofia, what do you think?", "scope": "public"},
    )
    _wait_jobs(client, world_id, timeout=45.0, services=services)
    cur = services.store.conn.execute(
        """SELECT characterId, continueDepth, trigger, status FROM GenerationJob
           WHERE worldId = ? AND sceneId = ? ORDER BY createdAt""",
        (world_id, lobby),
    ).fetchall()
    assert len(cur) >= 2
    done = [row for row in cur if row[3] == "done"]
    assert len(done) >= 2
    speakers = {row[0] for row in done}
    assert len(speakers) >= 1


def test_oq1_quality_addendum(tmp_path: Path) -> None:
    settings = Settings(models_dir=Path(__file__).resolve().parents[1] / "config" / "models")
    text = quality_addendum(settings)
    assert "in character" in text.lower()
