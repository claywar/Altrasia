"""COM-ACC / DEB-ACC post-v1 golden paths ([17] §8, [23] §8)."""

import time
from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


def _wait_jobs(client: TestClient, world_id: str, timeout: float = 12.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        q = client.get(f"/api/v1/worlds/{world_id}/queue").json()
        if not q.get("busy") and q.get("depth", 0) == 0:
            return
        time.sleep(0.1)
    raise TimeoutError("generation did not finish")


def test_com_acc1_mind_recall_other_scene(tmp_path: Path) -> None:
    """COM-ACC-1: commission locus in mandatory recall after scene change."""
    settings = Settings(
        db_path=tmp_path / "acc1.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall, kitchen = "scene-hall", "scene-kitchen"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": kitchen,
            "brief": "Catalog the spice jars.",
        },
    ).json()
    if com["status"] == "queued":
        client.post(f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}/start")
    _wait_jobs(client, world_id)
    final = next(
        c
        for c in client.get(f"/api/v1/worlds/{world_id}/commissions").json()
        if c["commissionId"] == com["commissionId"]
    )
    assert final["status"] == "done"
    prefix = final["deliverableLocusPrefix"]
    assert any(k.startswith(prefix) for k in final["deliverableLocusKeys"])

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/presence/join",
        json={"characterId": "char-alice"},
    )
    recall = svc.memory.build_mandatory_recall(
        character_id="char-alice",
        scene_id=hall,
        world_id=world_id,
    )
    assert f"{prefix}summary" in recall
    assert "Mock commission findings" in recall


def test_com_acc3_done_without_deliverable_rejected(tmp_path: Path) -> None:
    """COM-ACC-3: done without mind store or force reason is rejected."""
    settings = Settings(
        db_path=tmp_path / "acc3.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    client = TestClient(create_app(settings))
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-bob",
            "targetSceneId": "scene-hall",
            "brief": "Quick check",
        },
    ).json()
    blocked = client.patch(
        f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}",
        json={"status": "done"},
    )
    assert blocked.status_code == 400
    ok = client.post(
        f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}/force-complete",
        json={"reason": "Abandoned"},
    )
    assert ok.status_code == 200
    assert ok.json()["status"] == "done"


def test_deb_acc1_debate_mind_other_scene(tmp_path: Path) -> None:
    """DEB-ACC-1: debate synthesis loci recallable from another scene."""
    settings = Settings(
        db_path=tmp_path / "debacc.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    hall, kitchen = "scene-hall", "scene-kitchen"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{hall}/debate",
        json={"speakingOrder": ["char-alice"], "phase": "synthesis"},
    )
    _wait_jobs(client, world_id)
    mind = client.get(f"/api/v1/worlds/{world_id}/characters/char-alice/mind").json()
    assert any(k.get("locusKey", "").startswith(f"debate:{hall}:") for k in mind)

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    recall = svc.memory.build_mandatory_recall(
        character_id="char-alice",
        scene_id=kitchen,
        world_id=world_id,
    )
    assert f"debate:{hall}:" in recall


def test_com4_world_pool_deliverable(tmp_path: Path) -> None:
    settings = Settings(
        db_path=tmp_path / "com4.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    svc = app.state.services
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    kitchen = "scene-kitchen"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-alice"},
    )
    com = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-alice",
            "targetSceneId": kitchen,
            "brief": "Post findings on the board.",
            "deliverablePolicy": "both",
        },
    ).json()
    if com["status"] == "queued":
        client.post(f"/api/v1/worlds/{world_id}/commissions/{com['commissionId']}/start")
    _wait_jobs(client, world_id)
    world_loci = svc.store.conn.execute(
        "SELECT locusKey FROM Locus WHERE pool = 'world' AND ownerId = ?",
        (kitchen,),
    ).fetchall()
    assert any("commission:" in r[0] for r in world_loci)
