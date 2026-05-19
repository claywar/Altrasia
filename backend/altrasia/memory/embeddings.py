from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import struct
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from altrasia.inference.openai_compat import embeddings_url

log = logging.getLogger(__name__)
ISO = lambda: datetime.now(timezone.utc).isoformat()


class EmbeddingService:
    """INF-13: debounced embed jobs; no-op when embed URL unset."""

    def __init__(self, services: Any) -> None:
        self.svc = services
        self._pending: dict[str, asyncio.Task] = {}
        self._debounce_seconds = 2.0

    def _effective(self) -> dict:
        from altrasia.operator_settings import resolve_inference

        return resolve_inference(self.svc.settings, self.svc.operator_settings.load())

    @property
    def enabled(self) -> bool:
        return bool(self._effective().get("embeddingBaseUrl"))

    def schedule_embed(
        self,
        *,
        owner_scope: str,
        owner_id: str,
        source_type: str,
        source_ref: str,
        text: str,
    ) -> None:
        if not self.enabled or not text.strip():
            return
        key = f"{owner_scope}:{owner_id}:{source_ref}"
        prev = self._pending.pop(key, None)
        if prev and not prev.done():
            prev.cancel()

        async def _run() -> None:
            await asyncio.sleep(self._debounce_seconds)
            await self._embed_and_store(
                owner_scope=owner_scope,
                owner_id=owner_id,
                source_type=source_type,
                source_ref=source_ref,
                text=text,
            )

        self._pending[key] = asyncio.create_task(_run())

    async def _embed_and_store(
        self,
        *,
        owner_scope: str,
        owner_id: str,
        source_type: str,
        source_ref: str,
        text: str,
    ) -> None:
        vec = await self._fetch_vector(text)
        if not vec:
            return
        record_id = str(uuid.uuid4())
        source_id = f"{owner_id}:{source_ref}"
        blob = struct.pack(f"{len(vec)}f", *vec)
        content_hash = hashlib.sha256(text.encode()).hexdigest()
        self.svc.store.run(
            """INSERT OR REPLACE INTO EmbeddingRecord
               (recordId, sourceType, sourceId, ownerScope, vectorBlob, textHash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (record_id, source_type, source_id, owner_scope, blob, content_hash),
        )
        self.svc.store.commit()

    async def _fetch_vector(self, text: str) -> list[float] | None:
        eff = self._effective()
        base = eff.get("embeddingBaseUrl")
        if not base:
            return _hash_embed(text)
        url = embeddings_url(str(base))
        payload = {"model": eff.get("embeddingModel"), "input": text[:8000]}
        try:

            async def work() -> list[float]:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    r = await client.post(url, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return list(data["data"][0]["embedding"])

            return await self.svc.gpu_queue.run(str(uuid.uuid4()), "embed", work)
        except Exception as exc:
            log.warning("embed failed: %s", exc)
            return _hash_embed(text)


def _hash_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic pseudo-embedding for tests without embed server."""
    out: list[float] = []
    for i in range(dim):
        h = hashlib.sha256(f"{i}:{text}".encode()).digest()
        out.append((h[0] / 255.0) * 2 - 1)
    return out


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def vector_from_blob(blob: bytes | None) -> list[float] | None:
    if not blob:
        return None
    n = len(blob) // 4
    if n == 0:
        return None
    return list(struct.unpack(f"{n}f", blob))
