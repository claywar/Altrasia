-- Phase 6: MapDraft proposals (MAP-AUTH-5)
CREATE TABLE IF NOT EXISTS LayoutDraft (
  layoutDraftId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL,
  operatorBrief TEXT NOT NULL,
  scope TEXT NOT NULL,
  proposedJson TEXT,
  status TEXT NOT NULL,
  errorMessage TEXT,
  revision INTEGER NOT NULL DEFAULT 0,
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_layout_draft_world ON LayoutDraft(worldId, status);
