"""COM-ACC / DEB-ACC post-v1 golden paths ([17] §8, [23] §8)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from tests.conftest import make_test_settings, wait_for_jobs as _wait_jobs


def test_com_acc1_mind_recall_other_scene(tmp_path: Path) -> None:
    """COM-ACC-1: commission locus in mandatory recall after scene change."""
    settings = make_test_settings(tmp_path, "acc1.db")
    with TestClient(create_app(settings)) as client:
        svc = client.app.state.services
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        hall, kitchen = "scene-lobby", "scene-conference-room"
        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
            json={"characterId": "char-jordan-reyes"},
        )
        com = client.post(
            f"/api/v1/worlds/{world_id}/commissions",
            json={
                "assigneeCharacterId": "char-jordan-reyes",
                "targetSceneId": kitchen,
                "brief": "Catalog open platform incidents from the sprint retro.",
            },
        ).json()
        _wait_jobs(client, world_id, timeout=45.0)
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
            json={"characterId": "char-jordan-reyes"},
        )
        recall = svc.memory.build_mandatory_recall(
            character_id="char-jordan-reyes",
            scene_id=hall,
            world_id=world_id,
        )
        assert f"{prefix}summary" in recall
        assert "Mock commission findings" in recall


def test_com_acc3_done_without_deliverable_rejected(tmp_path: Path) -> None:
    """COM-ACC-3: done without mind store or force reason is rejected."""
    settings = make_test_settings(tmp_path, "acc3.db")
    with TestClient(create_app(settings)) as client:
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        com = client.post(
            f"/api/v1/worlds/{world_id}/commissions",
            json={
                "assigneeCharacterId": "char-sofia-mendez",
                "targetSceneId": "scene-lobby",
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
    settings = make_test_settings(tmp_path, "debacc.db")
    with TestClient(create_app(settings)) as client:
        svc = client.app.state.services
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        hall, kitchen = "scene-lobby", "scene-conference-room"
        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{hall}/debate",
            json={"speakingOrder": ["char-jordan-reyes"], "phase": "synthesis"},
        )
        _wait_jobs(client, world_id, timeout=45.0)
        mind = client.get(
            f"/api/v1/worlds/{world_id}/characters/char-jordan-reyes/mind"
        ).json()
        assert any(k.get("locusKey", "").startswith(f"debate:{hall}:") for k in mind)

        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
            json={"characterId": "char-jordan-reyes"},
        )
        recall = svc.memory.build_mandatory_recall(
            character_id="char-jordan-reyes",
            scene_id=kitchen,
            world_id=world_id,
        )
        assert f"debate:{hall}:" in recall


def test_com4_world_pool_deliverable(tmp_path: Path) -> None:
    settings = make_test_settings(tmp_path, "com4.db")
    with TestClient(create_app(settings)) as client:
        svc = client.app.state.services
        world_id = client.post(
            "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
        ).json()["worldId"]
        kitchen = "scene-conference-room"
        client.post(
            f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
            json={"characterId": "char-jordan-reyes"},
        )
        com = client.post(
            f"/api/v1/worlds/{world_id}/commissions",
            json={
                "assigneeCharacterId": "char-jordan-reyes",
                "targetSceneId": kitchen,
                "brief": "Post sprint retro findings on the team board.",
                "deliverablePolicy": "both",
            },
        ).json()
        _wait_jobs(client, world_id, timeout=45.0)
        world_loci = svc.store.conn.execute(
            "SELECT locusKey FROM Locus WHERE pool = 'world' AND ownerId = ?",
            (kitchen,),
        ).fetchall()
        assert any("commission:" in r[0] for r in world_loci)
