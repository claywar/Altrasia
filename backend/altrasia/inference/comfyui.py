from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx

log = logging.getLogger(__name__)


async def generate_portrait(
    services: Any,
    *,
    character_id: str,
    prompt: str,
    job_id: str | None = None,
) -> dict[str, Any]:
    """IMG-1: queue image work via GpuResourceQueue; yields to chat lease."""
    base = services.settings.comfy_url
    if not base:
        return {
            "ok": True,
            "mock": True,
            "portraitUrl": None,
            "message": "ComfyUI not configured — gray placeholder only",
        }
    jid = job_id or str(uuid.uuid4())

    async def work() -> dict[str, Any]:
        payload = {"prompt": prompt[:500], "characterId": character_id}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{base.rstrip('/')}/altrasia/portrait", json=payload)
            r.raise_for_status()
            return r.json()

    try:
        return await services.gpu_queue.run(jid, "image", work)
    except Exception as exc:
        log.warning("comfyui portrait failed: %s", exc)
        return {"ok": False, "error": str(exc)}
