from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from altrasia.domain.inventory import format_fixture_summary

ISO = lambda: datetime.now(timezone.utc).isoformat()


def sync_scene_fixtures_to_loci(
    store: Any,
    *,
    scene_id: str,
    updated_at: str | None = None,
) -> list[str]:
    """LP-4 / MP-2: one-way mirror of scene fixtures into world pool loci."""
    scene = store.get_scene(scene_id)
    if not scene:
        return []
    ts = updated_at or ISO()
    prefix = f"location:{scene_id}:"
    store.conn.execute(
        """DELETE FROM Locus WHERE pool = 'world' AND ownerId = ? AND locusKey LIKE ?""",
        (scene_id, f"{prefix}%"),
    )
    written: list[str] = []
    name = scene.get("locationName", scene_id)
    desc = (scene.get("locationDescription") or "").strip()
    scene_val = f"[{name}] {desc}".strip()
    store.upsert_locus("world", scene_id, f"{prefix}__scene__", scene_val, ts)
    written.append(f"{prefix}__scene__")

    fixtures = json.loads(scene.get("fixturesJson") or "{}")
    for key in sorted(fixtures.keys()):
        fixture = fixtures[key]
        line = format_fixture_summary(key, fixture)
        if fixture.get("description"):
            line = f"{line} — {fixture['description']}"
        locus_key = f"{prefix}{key}"
        store.upsert_locus("world", scene_id, locus_key, line, ts)
        written.append(locus_key)
    store.conn.commit()
    return written
