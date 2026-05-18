"""Operator inference settings and model catalog."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from altrasia.api.app import create_app
from altrasia.config import Settings


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, object]:
    settings = Settings(
        data_dir=tmp_path,
        mock_llm=True,
        llm_base_url="http://env-primary:8080",
        llm_model="env-chat-model",
        embed_base_url="http://env-embed:8081",
        embed_model="env-embed-model",
        fixtures_dir=Path(__file__).resolve().parent / "fixtures",
    )
    app = create_app(settings)
    return TestClient(app), app.state.services


def test_inference_settings_patch_and_apply(client: tuple[TestClient, object]) -> None:
    client, services = client
    r = client.patch(
        "/api/v1/operator/settings",
        json={
            "inference": {
                "primaryBaseUrl": "http://remote:9000",
                "primaryModel": "Qwen3-35B",
                "embeddingBaseUrl": "http://remote:9001",
                "embeddingModel": "embed-model",
            }
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["inference"]["primaryModel"] == "Qwen3-35B"
    assert body["inferenceEffective"]["primaryBaseUrl"] == "http://remote:9000"
    assert body["inferenceEffective"]["mockLlm"] is False
    assert services.llm.base_url == "http://remote:9000"
    assert services.llm.model == "Qwen3-35B"
    assert services.llm.mock is False
    assert services.embeddings.enabled is True


def test_inference_settings_fall_back_to_env(client: tuple[TestClient, object]) -> None:
    client, services = client
    r = client.get("/api/v1/operator/settings")
    assert r.status_code == 200
    eff = r.json()["inferenceEffective"]
    assert eff["primaryBaseUrl"] == "http://env-primary:8080"
    assert eff["primaryModel"] == "env-chat-model"
    assert eff["embeddingBaseUrl"] == "http://env-embed:8081"
    assert services.llm.mock is False


@pytest.mark.asyncio
async def test_list_inference_models_endpoint(client: tuple[TestClient, object]) -> None:
    client, _ = client
    mock_payload = {
        "ok": True,
        "models": [{"id": "model-a"}, {"id": "model-b"}],
        "error": None,
        "routerMode": True,
    }

    with patch(
        "altrasia.inference.model_catalog.list_openai_models",
        new_callable=AsyncMock,
        return_value=mock_payload,
    ):
        r = client.get(
            "/api/v1/operator/inference/models",
            params={"target": "primary", "baseUrl": "http://router:8080"},
        )
    assert r.status_code == 200
    data = r.json()
    assert data["target"] == "primary"
    assert data["ok"] is True
    assert len(data["models"]) == 2
    assert data["routerMode"] is True
