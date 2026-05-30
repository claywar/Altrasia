CREATE TABLE IF NOT EXISTS ReflectionRun (
  runId TEXT PRIMARY KEY,
  characterId TEXT NOT NULL,
  worldId TEXT,
  trigger TEXT NOT NULL,
  inputSegmentIdsJson TEXT,
  inputMessageCount INTEGER DEFAULT 0,
  outputLociJson TEXT,
  outputLinkCount INTEGER DEFAULT 0,
  status TEXT NOT NULL,
  errorText TEXT,
  startedAt TEXT NOT NULL,
  completedAt TEXT
);
CREATE INDEX IF NOT EXISTS idx_reflectionrun_char ON ReflectionRun(characterId, startedAt DESC);

CREATE TABLE IF NOT EXISTS MemoryLink (
  linkId TEXT PRIMARY KEY,
  characterId TEXT NOT NULL,
  fromKind TEXT NOT NULL,
  fromRef TEXT NOT NULL,
  relation TEXT NOT NULL,
  toKind TEXT NOT NULL,
  toRef TEXT NOT NULL,
  weight REAL DEFAULT 1.0,
  summary TEXT,
  sourceReflectionId TEXT,
  createdAt TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memorylink_char ON MemoryLink(characterId, relation);

CREATE TABLE IF NOT EXISTS PersonaProposal (
  proposalId TEXT PRIMARY KEY,
  characterId TEXT NOT NULL,
  reflectionRunId TEXT,
  field TEXT NOT NULL,
  proposedValue TEXT NOT NULL,
  rationale TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  createdAt TEXT NOT NULL,
  resolvedAt TEXT
);
CREATE INDEX IF NOT EXISTS idx_personaproposal_char ON PersonaProposal(characterId, status);
