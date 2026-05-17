-- Phase 3: character authoring drafts (CHAR-2 — not a Character until approved)
CREATE TABLE IF NOT EXISTS CharacterDraft (
  draftId TEXT PRIMARY KEY,
  operatorBrief TEXT NOT NULL,
  definitionJson TEXT,
  status TEXT NOT NULL,
  errorMessage TEXT,
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);
