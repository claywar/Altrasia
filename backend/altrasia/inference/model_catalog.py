from __future__ import annotations

from typing import Any

import httpx


def _normalize_base_url(base_url: str) -> str:
    url = base_url.strip().rstrip("/")
    if url.endswith("/v1"):
        return url
    return url + "/v1"


async def list_openai_models(base_url: str | None) -> dict[str, Any]:
    """List model ids from an OpenAI-compatible server (llama.cpp router, etc.)."""
    if not base_url or not str(base_url).strip():
        return {
            "ok": False,
            "models": [],
            "error": "No base URL configured",
            "routerMode": False,
        }
    url = _normalize_base_url(str(base_url)) + "/models"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "models": [],
            "error": str(exc),
            "routerMode": None,
        }
    except Exception as exc:
        return {
            "ok": False,
            "models": [],
            "error": str(exc),
            "routerMode": None,
        }

    rows = data.get("data")
    if not isinstance(rows, list):
        return {
            "ok": False,
            "models": [],
            "error": "Unexpected /v1/models response shape",
            "routerMode": False,
        }

    models: list[dict[str, str]] = []
    for row in rows:
        if isinstance(row, dict):
            mid = row.get("id") or row.get("name")
            if mid:
                models.append({"id": str(mid)})
        elif isinstance(row, str):
            models.append({"id": row})

    models.sort(key=lambda m: m["id"].lower())
    router_mode = len(models) > 1
    return {
        "ok": True,
        "models": models,
        "error": None,
        "routerMode": router_mode,
    }
