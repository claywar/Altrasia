"""World outfit presets (OP-1–4)."""

from pathlib import Path

from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings
from altrasia.domain.inventory import apply_outfit_preset, get_outfit_presets


def _client(tmp_path: Path) -> tuple[TestClient, str]:
    settings = Settings(
        db_path=tmp_path / "outfit.db",
        mock_llm=True,
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    client = TestClient(app)
    world_id = client.post("/api/v1/worlds", json={"fixtureId": "demo-spatial-v1"}).json()[
        "worldId"
    ]
    return client, world_id


def test_demo_outfit_presets_loaded(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    store = client.app.state.services.store  # type: ignore[attr-defined]
    presets = get_outfit_presets(store, world_id)
    assert "vertex-formal" in presets
    assert presets["vertex-formal"]["displayName"] == "Vertex formal"


def test_apply_outfit_preset_api(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    cid = "char-jordan-reyes"
    out = client.post(
        f"/api/v1/worlds/{world_id}/characters/{cid}/outfit/apply",
        json={"presetId": "vertex-formal"},
    ).json()
    assert out["presetId"] == "vertex-formal"
    worn = out["inventory"]["worn"]
    assert any("blazer" in (i.get("label") or "").lower() for i in worn)


def test_apply_outfit_preset_domain(tmp_path: Path) -> None:
    client, world_id = _client(tmp_path)
    store = client.app.state.services.store  # type: ignore[attr-defined]
    cid = "char-sofia-chen"
    result = apply_outfit_preset(
        store, world_id=world_id, character_id=cid, preset_id="lab-ppe"
    )
    labels = [i.get("label", "") for i in result["inventory"]["worn"]]
    assert any("lab coat" in x for x in labels)
