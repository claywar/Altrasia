from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_MIGRATIONS_DIR = Path(__file__).parent / "sqlite" / "migrations"


class SqlitePersistence:
    """SQLite implementation of PersistencePort (DM-8, DM-9)."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def migrate(self) -> None:
        for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
            self.conn.executescript(path.read_text(encoding="utf-8"))
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _row(self, row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return dict(row)

    def _rows(self, rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(r) for r in rows]

    def list_worlds(self) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM World ORDER BY createdAt DESC")
        return self._rows(cur.fetchall())

    def get_world(self, world_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM World WHERE worldId = ?", (world_id,))
        return self._row(cur.fetchone())

    def insert_world(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO World (worldId, name, activeSceneId, defaultModelProfile, configJson,
               worldMapJson, eventSeq, createdAt, updatedAt)
               VALUES (:worldId, :name, :activeSceneId, :defaultModelProfile, :configJson,
               :worldMapJson, :eventSeq, :createdAt, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def update_world(self, world_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [world_id]
        self.conn.execute(f"UPDATE World SET {cols} WHERE worldId = ?", vals)
        self.conn.commit()

    def bump_event_seq(self, world_id: str) -> int:
        self.conn.execute(
            "UPDATE World SET eventSeq = eventSeq + 1, updatedAt = datetime('now') WHERE worldId = ?",
            (world_id,),
        )
        self.conn.commit()
        w = self.get_world(world_id)
        return int(w["eventSeq"]) if w else 0

    def list_scenes(self, world_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM Scene WHERE worldId = ? ORDER BY locationName", (world_id,)
        )
        return self._rows(cur.fetchall())

    def get_scene(self, scene_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM Scene WHERE sceneId = ?", (scene_id,))
        return self._row(cur.fetchone())

    def insert_scene(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Scene (sceneId, worldId, structureId, mapLevel, levelLabel,
               planPositionJson, mapArtifactJson, locationName, locationDescription, presentJson,
               fixturesJson, exitsJson, activityJson, roundRobinIndex, layoutHintsJson, updatedAt)
               VALUES (:sceneId, :worldId, :structureId, :mapLevel, :levelLabel,
               :planPositionJson, :mapArtifactJson, :locationName, :locationDescription, :presentJson,
               :fixturesJson, :exitsJson, :activityJson, :roundRobinIndex, :layoutHintsJson, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def update_scene(self, scene_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [scene_id]
        self.conn.execute(f"UPDATE Scene SET {cols} WHERE sceneId = ?", vals)
        self.conn.commit()

    def insert_character(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Character (characterId, displayName, definitionJson, modelProfile,
               speechWeight, createdAt) VALUES (:characterId, :displayName, :definitionJson,
               :modelProfile, :speechWeight, :createdAt)""",
            row,
        )
        self.conn.commit()

    def get_character(self, character_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM Character WHERE characterId = ?", (character_id,))
        return self._row(cur.fetchone())

    def insert_character_draft(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO CharacterDraft (draftId, operatorBrief, definitionJson, status,
               errorMessage, createdAt, updatedAt)
               VALUES (:draftId, :operatorBrief, :definitionJson, :status,
               :errorMessage, :createdAt, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def get_character_draft(self, draft_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM CharacterDraft WHERE draftId = ?", (draft_id,)
        )
        return self._row(cur.fetchone())

    def update_character_draft(self, draft_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [draft_id]
        self.conn.execute(f"UPDATE CharacterDraft SET {cols} WHERE draftId = ?", vals)
        self.conn.commit()

    def insert_layout_draft(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO LayoutDraft (layoutDraftId, worldId, operatorBrief, scope,
               proposedJson, status, errorMessage, revision, createdAt, updatedAt)
               VALUES (:layoutDraftId, :worldId, :operatorBrief, :scope,
               :proposedJson, :status, :errorMessage, :revision, :createdAt, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def get_layout_draft(self, draft_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM LayoutDraft WHERE layoutDraftId = ?", (draft_id,)
        )
        return self._row(cur.fetchone())

    def update_layout_draft(self, draft_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [draft_id]
        self.conn.execute(f"UPDATE LayoutDraft SET {cols} WHERE layoutDraftId = ?", vals)
        self.conn.commit()

    def add_world_member(self, world_id: str, character_id: str, **kw: Any) -> None:
        self.conn.execute(
            """INSERT OR IGNORE INTO WorldMember (worldId, characterId, muted, disabled, sceneRole)
               VALUES (?, ?, ?, ?, ?)""",
            (
                world_id,
                character_id,
                kw.get("muted", 0),
                kw.get("disabled", 0),
                kw.get("sceneRole"),
            ),
        )
        self.conn.commit()

    def list_world_characters(self, world_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT c.*, wm.muted, wm.disabled, wm.sceneRole FROM Character c
               JOIN WorldMember wm ON wm.characterId = c.characterId
               WHERE wm.worldId = ?""",
            (world_id,),
        )
        return self._rows(cur.fetchall())

    def list_messages(
        self, world_id: str, *, scene_id: str | None = None, channel_kind: str = "scene"
    ) -> list[dict[str, Any]]:
        join = """LEFT JOIN GenerationJob j ON j.jobId = m.generationJobId"""
        cols = "m.*, j.trigger AS generationTrigger, j.selectionRationaleJson AS jobRationaleJson"
        if scene_id:
            cur = self.conn.execute(
                f"""SELECT {cols} FROM Message m {join}
                   WHERE m.worldId = ? AND m.channelKind = ? AND m.sceneId = ?
                   ORDER BY m.createdAt""",
                (world_id, channel_kind, scene_id),
            )
        else:
            cur = self.conn.execute(
                f"""SELECT {cols} FROM Message m {join}
                   WHERE m.worldId = ? AND m.channelKind = ?
                   ORDER BY m.createdAt""",
                (world_id, channel_kind),
            )
        return self._rows(cur.fetchall())

    def insert_message(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Message (messageId, worldId, channelKind, sceneId, role, characterId,
               outputText, reasoning, streamStatus, generationJobId, metaJson, createdAt)
               VALUES (:messageId, :worldId, :channelKind, :sceneId, :role, :characterId,
               :outputText, :reasoning, :streamStatus, :generationJobId, :metaJson, :createdAt)""",
            row,
        )
        self.conn.commit()

    def update_message(self, message_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [message_id]
        self.conn.execute(f"UPDATE Message SET {cols} WHERE messageId = ?", vals)
        self.conn.commit()

    def upsert_locus(self, pool: str, owner_id: str, locus_key: str, value: str, updated_at: str) -> None:
        self.conn.execute(
            """INSERT INTO Locus (locusKey, pool, ownerId, value, updatedAt)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(pool, ownerId, locusKey) DO UPDATE SET value = excluded.value,
               updatedAt = excluded.updatedAt""",
            (locus_key, pool, owner_id, value, updated_at),
        )
        self.conn.commit()

    def search_loci(self, pool: str, owner_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT l.locusKey, l.pool, l.ownerId, l.value, l.updatedAt
               FROM LocusFts f
               JOIN Locus l ON l.rowid = f.rowid
               WHERE LocusFts MATCH ? AND l.pool = ? AND l.ownerId = ?
               LIMIT ?""",
            (query, pool, owner_id, limit),
        )
        return self._rows(cur.fetchall())

    def append_diary(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO DiarySegment (segmentId, characterId, text, sourceSceneId,
               messageIdsJson, dedupeKey, kind, createdAt)
               VALUES (:segmentId, :characterId, :text, :sourceSceneId,
               :messageIdsJson, :dedupeKey, :kind, :createdAt)""",
            row,
        )
        self.conn.commit()

    def list_diary(self, character_id: str, limit: int = 20) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT * FROM DiarySegment WHERE characterId = ?
               ORDER BY createdAt DESC LIMIT ?""",
            (character_id, limit),
        )
        return list(reversed(self._rows(cur.fetchall())))

    def search_diary(self, character_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT d.* FROM DiaryFts f
               JOIN DiarySegment d ON d.rowid = f.rowid
               WHERE DiaryFts MATCH ? AND d.characterId = ?
               ORDER BY d.createdAt DESC LIMIT ?""",
            (query, character_id, limit),
        )
        return self._rows(cur.fetchall())

    def list_channels(self, world_id: str, *, active_only: bool = True) -> list[dict[str, Any]]:
        if active_only:
            cur = self.conn.execute(
                "SELECT * FROM CommChannel WHERE worldId = ? AND active = 1",
                (world_id,),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM CommChannel WHERE worldId = ?", (world_id,)
            )
        return self._rows(cur.fetchall())

    def get_channel(self, channel_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM CommChannel WHERE channelId = ?", (channel_id,)
        )
        return self._row(cur.fetchone())

    def insert_channel(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO CommChannel (channelId, worldId, endpointsJson, participantsJson, active)
               VALUES (:channelId, :worldId, :endpointsJson, :participantsJson, :active)""",
            row,
        )
        self.conn.commit()

    def update_channel(self, channel_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [channel_id]
        self.conn.execute(f"UPDATE CommChannel SET {cols} WHERE channelId = ?", vals)
        self.conn.commit()

    def get_signal(self, signal_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM CrossSceneSignal WHERE signalId = ?", (signal_id,)
        )
        return self._row(cur.fetchone())

    def list_signals(self, world_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            cur = self.conn.execute(
                "SELECT * FROM CrossSceneSignal WHERE worldId = ? AND status = ? ORDER BY createdAt DESC",
                (world_id, status),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM CrossSceneSignal WHERE worldId = ? ORDER BY createdAt DESC",
                (world_id,),
            )
        return self._rows(cur.fetchall())

    def insert_signal(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO CrossSceneSignal (signalId, worldId, kind, sourceSceneId, targetSceneId,
               fromCharacterId, status, createdAt)
               VALUES (:signalId, :worldId, :kind, :sourceSceneId, :targetSceneId,
               :fromCharacterId, :status, :createdAt)""",
            row,
        )
        self.conn.commit()

    def update_signal(self, signal_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [signal_id]
        self.conn.execute(f"UPDATE CrossSceneSignal SET {cols} WHERE signalId = ?", vals)
        self.conn.commit()

    def insert_job(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO GenerationJob (jobId, worldId, characterId, sceneId, trigger, priority,
               observerMode, status, continueDepth, triggerMessageId, selectionRationaleJson, createdAt)
               VALUES (:jobId, :worldId, :characterId, :sceneId, :trigger, :priority,
               :observerMode, :status, :continueDepth, :triggerMessageId, :selectionRationaleJson,
               :createdAt)""",
            row,
        )
        self.conn.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute("SELECT * FROM GenerationJob WHERE jobId = ?", (job_id,))
        return self._row(cur.fetchone())

    def update_job(self, job_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [job_id]
        self.conn.execute(f"UPDATE GenerationJob SET {cols} WHERE jobId = ?", vals)
        self.conn.commit()

    def list_queued_jobs(self, world_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT * FROM GenerationJob WHERE worldId = ? AND status IN ('queued', 'running')
               ORDER BY priority DESC, createdAt""",
            (world_id,),
        )
        return self._rows(cur.fetchall())

    def list_structures(self, world_id: str) -> list[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM Structure WHERE worldId = ?", (world_id,))
        return self._rows(cur.fetchall())

    def insert_structure(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Structure (structureId, worldId, displayName, kind, boundaryJson, updatedAt)
               VALUES (:structureId, :worldId, :displayName, :kind, :boundaryJson, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def insert_commission(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Commission (commissionId, worldId, assigneeCharacterId, targetSceneId,
               brief, status, deliverablePolicy, deliverableLocusPrefix, deliverableLocusKeysJson,
               allowedToolsJson, forceCompleteReason, createdAt, updatedAt)
               VALUES (:commissionId, :worldId, :assigneeCharacterId, :targetSceneId, :brief,
               :status, :deliverablePolicy, :deliverableLocusPrefix, :deliverableLocusKeysJson,
               :allowedToolsJson, :forceCompleteReason, :createdAt, :updatedAt)""",
            row,
        )
        self.conn.commit()

    def get_commission(self, commission_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM Commission WHERE commissionId = ?", (commission_id,)
        )
        return self._row(cur.fetchone())

    def list_commissions(
        self, world_id: str, *, status: str | None = None
    ) -> list[dict[str, Any]]:
        if status:
            cur = self.conn.execute(
                """SELECT * FROM Commission WHERE worldId = ? AND status = ?
                   ORDER BY createdAt DESC""",
                (world_id, status),
            )
        else:
            cur = self.conn.execute(
                "SELECT * FROM Commission WHERE worldId = ? ORDER BY createdAt DESC",
                (world_id,),
            )
        return self._rows(cur.fetchall())

    def update_commission(self, commission_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [commission_id]
        self.conn.execute(f"UPDATE Commission SET {cols} WHERE commissionId = ?", vals)
        self.conn.commit()

    def insert_approval(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO Approval (approvalId, worldId, toolName, paramsJson, state, createdAt)
               VALUES (:approvalId, :worldId, :toolName, :paramsJson, :state, :createdAt)""",
            row,
        )
        self.conn.commit()

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT * FROM Approval WHERE approvalId = ?", (approval_id,)
        )
        return self._row(cur.fetchone())

    def list_approvals(
        self, world_id: str | None = None, *, state: str | None = None
    ) -> list[dict[str, Any]]:
        if world_id and state:
            cur = self.conn.execute(
                """SELECT * FROM Approval WHERE worldId = ? AND state = ?
                   ORDER BY createdAt DESC""",
                (world_id, state),
            )
        elif world_id:
            cur = self.conn.execute(
                "SELECT * FROM Approval WHERE worldId = ? ORDER BY createdAt DESC",
                (world_id,),
            )
        elif state:
            cur = self.conn.execute(
                "SELECT * FROM Approval WHERE state = ? ORDER BY createdAt DESC",
                (state,),
            )
        else:
            cur = self.conn.execute("SELECT * FROM Approval ORDER BY createdAt DESC")
        return self._rows(cur.fetchall())

    def update_approval(self, approval_id: str, **fields: Any) -> None:
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [approval_id]
        self.conn.execute(f"UPDATE Approval SET {cols} WHERE approvalId = ?", vals)
        self.conn.commit()

    def insert_evidence(self, row: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO EvidenceRecord (evidenceId, locusKey, pool, ownerId,
               sourceKind, sourceRef, retrievedAt, commissionId)
               VALUES (:evidenceId, :locusKey, :pool, :ownerId, :sourceKind,
               :sourceRef, :retrievedAt, :commissionId)""",
            row,
        )
        self.conn.commit()

    def list_evidence_for_locus(
        self, pool: str, owner_id: str, locus_key: str
    ) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            """SELECT * FROM EvidenceRecord WHERE pool = ? AND ownerId = ? AND locusKey = ?
               ORDER BY retrievedAt DESC""",
            (pool, owner_id, locus_key),
        )
        return self._rows(cur.fetchall())

    @staticmethod
    def json_loads(raw: str | None, default: Any = None) -> Any:
        if raw is None or raw == "":
            return default if default is not None else {}
        return json.loads(raw)
