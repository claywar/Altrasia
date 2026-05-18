from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

from altrasia.memory.strip_reasoning import is_durable_value_ok, strip_reasoning
from altrasia.persistence.sqlite_store import SqlitePersistence

ISO = lambda: datetime.now(timezone.utc).isoformat()


class MemoryService:
    def __init__(self, store: SqlitePersistence, *, hybrid_search_enabled: bool = False) -> None:
        self.store = store
        self.hybrid_search_enabled = hybrid_search_enabled

    def memory_store(
        self, *, pool: str, owner_id: str, locus_key: str, value: str
    ) -> dict[str, str]:
        cleaned = strip_reasoning(value)
        if not is_durable_value_ok(cleaned):
            raise ValueError("memory_store rejected empty or reasoning-only value (MP-16)")
        self.store.upsert_locus(pool, owner_id, locus_key, cleaned, ISO())
        return {"locusKey": locus_key, "pool": pool, "ownerId": owner_id}

    def memory_search(self, *, pool: str, owner_id: str, query: str, limit: int = 10) -> list[dict]:
        try:
            hits = self.store.search_loci(pool, owner_id, query, limit)
            if not self.hybrid_search_enabled:
                return hits
            return self._rerank_with_embeddings(pool, owner_id, query, hits, limit)
        except Exception:
            return []

    def _rerank_with_embeddings(
        self, pool: str, owner_id: str, query: str, hits: list[dict], limit: int
    ) -> list[dict]:
        from altrasia.memory.embeddings import _hash_embed, cosine_similarity

        from altrasia.memory.embeddings import vector_from_blob

        rows = self.store.conn.execute(
            """SELECT sourceId, vectorBlob FROM EmbeddingRecord
               WHERE ownerScope = ? AND sourceId LIKE ? LIMIT 200""",
            (pool, f"{owner_id}:%"),
        ).fetchall()
        if not rows:
            return hits[:limit]
        qvec = _hash_embed(query)
        emb_map: dict[str, list[float]] = {}
        for sid, blob in rows:
            vec = vector_from_blob(blob)
            if vec:
                key = sid.split(":", 1)[-1] if ":" in sid else sid
                emb_map[key] = vec
        scored: list[tuple[float, dict]] = []
        for h in hits:
            key = h.get("locusKey", "")
            vec = emb_map.get(key)
            boost = cosine_similarity(qvec, vec) if vec else 0.0
            scored.append((boost, h))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in scored[:limit]]

    def diary_search(self, *, character_id: str, query: str, limit: int = 10) -> list[dict]:
        try:
            return self.store.search_diary(character_id, query, limit)
        except Exception:
            return []

    def build_mandatory_recall(
        self,
        *,
        character_id: str,
        scene_id: str,
        world_id: str | None = None,
        max_chars: int = 4000,
    ) -> str:
        """MP-8, MP-11, MP-22: assemble diary tail + mind/world/commons loci for prompt."""
        from altrasia.commons import character_has_commons_access
        from altrasia.world_config import get_world_config

        parts: list[str] = []
        diary = self.store.list_diary(character_id, limit=12)
        if diary:
            parts.append("## Recent diary (witnessed)")
            for seg in diary[-8:]:
                parts.append(f"- {seg['text']}")
        mind = self.store.conn.execute(
            "SELECT locusKey, value FROM Locus WHERE pool = 'mind' AND ownerId = ? ORDER BY updatedAt DESC LIMIT 20",
            (character_id,),
        ).fetchall()
        if mind:
            parts.append("## Mind loci")
            for row in mind:
                parts.append(f"- {row[0]}: {row[1]}")
        world = self.store.conn.execute(
            "SELECT locusKey, value FROM Locus WHERE pool = 'world' AND ownerId = ? ORDER BY updatedAt DESC LIMIT 10",
            (scene_id,),
        ).fetchall()
        if world:
            parts.append("## Scene world pool")
            for row in world:
                parts.append(f"- {row[0]}: {row[1]}")
        if world_id:
            cfg = get_world_config(self.store, world_id)
            if character_has_commons_access(cfg, character_id):
                commons = self.store.conn.execute(
                    """SELECT locusKey, value FROM Locus
                       WHERE pool = 'commons' AND ownerId = ? ORDER BY updatedAt DESC LIMIT 12""",
                    (world_id,),
                ).fetchall()
                if commons:
                    parts.append("## Institutional records (commons)")
                    for row in commons:
                        parts.append(f"- {row[0]}: {row[1]}")
        text = "\n".join(parts)
        return text[:max_chars]

    def capture_diary_fanout(
        self,
        *,
        scene_id: str,
        present_ids: list[str],
        snippet: str,
        message_ids: list[str],
    ) -> None:
        """MP-20: same segment for every present cast member."""
        cleaned = strip_reasoning(snippet)
        if not is_durable_value_ok(cleaned):
            return
        dedupe_src = "|".join(sorted(message_ids))
        dedupe_key = hashlib.sha256(dedupe_src.encode()).hexdigest()[:32]
        now = ISO()
        for cid in present_ids:
            if cid == "__persona__":
                continue
            self.store.append_diary(
                {
                    "segmentId": str(uuid.uuid4()),
                    "characterId": cid,
                    "text": cleaned,
                    "sourceSceneId": scene_id,
                    "messageIdsJson": json.dumps(message_ids),
                    "dedupeKey": dedupe_key,
                    "kind": "witnessed",
                    "createdAt": now,
                }
            )
