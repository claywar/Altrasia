from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

ISO = lambda: datetime.now(timezone.utc).isoformat()


def write_links(
    store: Any,
    *,
    character_id: str,
    reflection_run_id: str,
    links: list[dict[str, Any]],
) -> int:
    count = 0
    for link in links:
        summary = (link.get("summary") or "").strip()
        if not summary:
            continue
        store.insert_memory_link(
            {
                "linkId": str(uuid.uuid4()),
                "characterId": character_id,
                "fromKind": str(link.get("fromKind") or "locus"),
                "fromRef": str(link.get("fromRef") or ""),
                "relation": str(link.get("relation") or "relates_to"),
                "toKind": str(link.get("toKind") or "locus"),
                "toRef": str(link.get("toRef") or ""),
                "weight": float(link.get("weight") or 1.0),
                "summary": summary[:2000],
                "sourceReflectionId": reflection_run_id,
                "createdAt": ISO(),
            }
        )
        count += 1
    return count


def neighbors_for_recall(
    store: Any,
    *,
    character_id: str,
    seed_refs: list[tuple[str, str]],
    limit: int = 8,
) -> list[str]:
    """Return output-only neighbor summaries for mandatory recall enrichment."""
    rows = store.neighbors_for_refs(character_id, seed_refs, limit=limit)
    lines: list[str] = []
    seen: set[str] = set()
    for row in rows:
        summary = (row.get("summary") or "").strip()
        if not summary or summary in seen:
            continue
        seen.add(summary)
        rel = row.get("relation") or "relates_to"
        lines.append(f"- ({rel}) {summary}")
    return lines
