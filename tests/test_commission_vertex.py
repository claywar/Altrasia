"""Regression: mock commission deliverable on Vertex Labs demo fixture."""

from fastapi.testclient import TestClient

from tests.conftest import wait_for_jobs


def test_commission_mock_deliverable_on_vertex_fixture(
    app_client: tuple[TestClient, object],
) -> None:
    client, _services = app_client
    world_id = client.post(
        "/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}
    ).json()["worldId"]
    target = "scene-conference-room"

    created = client.post(
        f"/api/v1/worlds/{world_id}/commissions",
        json={
            "assigneeCharacterId": "char-jordan-reyes",
            "targetSceneId": target,
            "brief": "Summarize sprint retro action items for the platform team.",
        },
    ).json()
    assert created["status"] == "blocked"
    cid = created["commissionId"]

    client.post(
        f"/api/v1/worlds/{world_id}/scenes/{target}/presence/join",
        json={"characterId": "char-jordan-reyes"},
    )
    wait_for_jobs(client, world_id)

    final = next(
        c
        for c in client.get(f"/api/v1/worlds/{world_id}/commissions").json()
        if c["commissionId"] == cid
    )
    assert final["status"] == "done"
    assert final["deliverableLocusKeys"]

    mind = client.get(
        f"/api/v1/worlds/{world_id}/characters/char-jordan-reyes/mind"
    ).json()
    assert any("commission:" in loc.get("locusKey", "") for loc in mind)
