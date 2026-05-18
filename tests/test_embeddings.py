"""Embedding pipeline (INF-13)."""

import asyncio
from pathlib import Path

import pytest

from altrasia.config import Settings
from altrasia.services import AppServices


@pytest.mark.asyncio
async def test_embed_schedule_writes_record(tmp_path: Path) -> None:
    settings = Settings(db_path=tmp_path / "emb.db", embed_base_url=None)
    svc = AppServices.create(settings)
    await svc.embeddings._embed_and_store(
        owner_scope="mind",
        owner_id="char-test",
        source_type="locus",
        source_ref="fact.1",
        text="Paris is the capital of France.",
    )
    row = svc.store.conn.execute(
        "SELECT COUNT(*) FROM EmbeddingRecord WHERE sourceId LIKE ?",
        ("char-test:%",),
    ).fetchone()
    assert row and row[0] >= 1
