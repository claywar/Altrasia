"""Commission allowedTools + mock webtools_invoke."""

from fastapi.testclient import TestClient

from tests.conftest import wait_for_jobs


def test_commission_with_webtools(app_client: tuple[TestClient, object]) -> None:
    client, _services = app_client
    world_id = client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    kitchen = "scene-conference-room"
    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{kitchen}/presence/join",
        json={"characterId": "char-jordan-reyes"},
    )

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": kitchen,
            "brief": "Research Vertex Labs public API status page online.",
            "allowedTools": ["webtools_invoke", "memory_store", "memory_search"],
        },
    ).json()
    cid = created["commissionId"]
    assert "webtools_invoke" in (created.get("allowedTools") or [])

    if created["status"] == "queued":
        start = client.post(f"/api/v1/worlds/{world_id}/commissions/{cid}/start")
        assert start.status_code == 200
    wait_for_jobs(client, world_id)

    done = client.get(f"/api/v1/worlds/{world_id}/commissions").json()
    final = next(c for c in done if c["commissionId"] == cid)
    assert final["status"] == "done"
    mind = client.get(
        f"/api/v1/worlds/{world_id}/characters/char-jordan-reyes/mind"
    ).json()
    assert any("commission:" in loc.get("locusKey", "") for loc in mind)
