-- Altrasia migration 001 (docs/11-data-model.md)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS World (
  worldId TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  activeSceneId TEXT,
  defaultModelProfile TEXT NOT NULL DEFAULT 'qwen3.6-35b-a3b',
  configJson TEXT NOT NULL DEFAULT '{}',
  worldMapJson TEXT,
  eventSeq INTEGER NOT NULL DEFAULT 0,
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Structure (
  structureId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  displayName TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT 'building',
  boundaryJson TEXT,
  updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Scene (
  sceneId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  structureId TEXT REFERENCES Structure(structureId),
  mapLevel INTEGER NOT NULL DEFAULT 0,
  levelLabel TEXT,
  planPositionJson TEXT,
  mapArtifactJson TEXT,
  locationName TEXT NOT NULL,
  locationDescription TEXT NOT NULL DEFAULT '',
  presentJson TEXT NOT NULL DEFAULT '[]',
  fixturesJson TEXT NOT NULL DEFAULT '{}',
  exitsJson TEXT NOT NULL DEFAULT '[]',
  activityJson TEXT,
  roundRobinIndex INTEGER NOT NULL DEFAULT 0,
  layoutHintsJson TEXT,
  updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Character (
  characterId TEXT PRIMARY KEY,
  displayName TEXT NOT NULL,
  definitionJson TEXT NOT NULL DEFAULT '{}',
  modelProfile TEXT NOT NULL DEFAULT 'qwen3.6-35b-a3b',
  speechWeight REAL NOT NULL DEFAULT 0.5,
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS WorldMember (
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  characterId TEXT NOT NULL REFERENCES Character(characterId) ON DELETE CASCADE,
  muted INTEGER NOT NULL DEFAULT 0,
  disabled INTEGER NOT NULL DEFAULT 0,
  sceneRole TEXT,
  PRIMARY KEY (worldId, characterId)
);

CREATE TABLE IF NOT EXISTS Message (
  messageId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  channelKind TEXT NOT NULL,
  sceneId TEXT,
  role TEXT NOT NULL,
  characterId TEXT,
  outputText TEXT NOT NULL DEFAULT '',
  reasoning TEXT,
  streamStatus TEXT NOT NULL DEFAULT 'final',
  generationJobId TEXT,
  metaJson TEXT NOT NULL DEFAULT '{}',
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Locus (
  locusKey TEXT NOT NULL,
  pool TEXT NOT NULL,
  ownerId TEXT NOT NULL,
  value TEXT NOT NULL,
  updatedAt TEXT NOT NULL,
  PRIMARY KEY (pool, ownerId, locusKey)
);

CREATE TABLE IF NOT EXISTS DiarySegment (
  segmentId TEXT PRIMARY KEY,
  characterId TEXT NOT NULL REFERENCES Character(characterId) ON DELETE CASCADE,
  text TEXT NOT NULL,
  sourceSceneId TEXT NOT NULL,
  messageIdsJson TEXT NOT NULL DEFAULT '[]',
  dedupeKey TEXT NOT NULL,
  kind TEXT,
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS CrossSceneSignal (
  signalId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  sourceSceneId TEXT NOT NULL,
  targetSceneId TEXT NOT NULL,
  fromCharacterId TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS CommChannel (
  channelId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  endpointsJson TEXT NOT NULL DEFAULT '[]',
  participantsJson TEXT NOT NULL DEFAULT '[]',
  active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS GenerationJob (
  jobId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  characterId TEXT NOT NULL,
  sceneId TEXT NOT NULL,
  trigger TEXT NOT NULL,
  priority INTEGER NOT NULL DEFAULT 0,
  observerMode TEXT,
  status TEXT NOT NULL DEFAULT 'queued',
  continueDepth INTEGER NOT NULL DEFAULT 0,
  triggerMessageId TEXT,
  selectionRationaleJson TEXT,
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS GpuLease (
  leaseId TEXT PRIMARY KEY,
  jobId TEXT NOT NULL REFERENCES GenerationJob(jobId) ON DELETE CASCADE,
  kind TEXT NOT NULL,
  startedAt TEXT NOT NULL,
  releasedAt TEXT
);

CREATE TABLE IF NOT EXISTS Approval (
  approvalId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  toolName TEXT NOT NULL,
  paramsJson TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  createdAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS EmbeddingRecord (
  recordId TEXT PRIMARY KEY,
  sourceType TEXT NOT NULL,
  sourceId TEXT NOT NULL,
  ownerScope TEXT NOT NULL,
  vectorBlob BLOB,
  textHash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Commission (
  commissionId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL REFERENCES World(worldId) ON DELETE CASCADE,
  assigneeCharacterId TEXT NOT NULL,
  targetSceneId TEXT NOT NULL,
  brief TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  deliverablePolicy TEXT NOT NULL DEFAULT 'mind',
  deliverableLocusPrefix TEXT,
  deliverableLocusKeysJson TEXT,
  allowedToolsJson TEXT,
  forceCompleteReason TEXT,
  createdAt TEXT NOT NULL,
  updatedAt TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS EvidenceRecord (
  evidenceId TEXT PRIMARY KEY,
  locusKey TEXT NOT NULL,
  pool TEXT NOT NULL,
  ownerId TEXT NOT NULL,
  sourceKind TEXT NOT NULL,
  sourceRef TEXT NOT NULL,
  retrievedAt TEXT NOT NULL,
  commissionId TEXT
);

CREATE INDEX IF NOT EXISTS idx_locus_pool_owner ON Locus(pool, ownerId);
CREATE INDEX IF NOT EXISTS idx_locus_pool_owner_key ON Locus(pool, ownerId, locusKey);
CREATE INDEX IF NOT EXISTS idx_diary_character_time ON DiarySegment(characterId, createdAt DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_diary_dedupe ON DiarySegment(characterId, dedupeKey);
CREATE INDEX IF NOT EXISTS idx_message_scene_time ON Message(sceneId, createdAt);
CREATE INDEX IF NOT EXISTS idx_message_world_channel ON Message(worldId, channelKind, createdAt);
CREATE INDEX IF NOT EXISTS idx_embedding_scope ON EmbeddingRecord(ownerScope, sourceType);
CREATE INDEX IF NOT EXISTS idx_signal_world_status ON CrossSceneSignal(worldId, status);

-- FTS5 external content
CREATE VIRTUAL TABLE IF NOT EXISTS LocusFts USING fts5(
  locusKey,
  value,
  content='Locus',
  content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS DiaryFts USING fts5(
  text,
  content='DiarySegment',
  content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS locus_ai AFTER INSERT ON Locus BEGIN
  INSERT INTO LocusFts(rowid, locusKey, value) VALUES (new.rowid, new.locusKey, new.value);
END;
CREATE TRIGGER IF NOT EXISTS locus_ad AFTER DELETE ON Locus BEGIN
  INSERT INTO LocusFts(LocusFts, rowid, locusKey, value) VALUES ('delete', old.rowid, old.locusKey, old.value);
END;
CREATE TRIGGER IF NOT EXISTS locus_au AFTER UPDATE ON Locus BEGIN
  INSERT INTO LocusFts(LocusFts, rowid, locusKey, value) VALUES ('delete', old.rowid, old.locusKey, old.value);
  INSERT INTO LocusFts(rowid, locusKey, value) VALUES (new.rowid, new.locusKey, new.value);
END;

CREATE TRIGGER IF NOT EXISTS diary_ai AFTER INSERT ON DiarySegment BEGIN
  INSERT INTO DiaryFts(rowid, text) VALUES (new.rowid, new.text);
END;
CREATE TRIGGER IF NOT EXISTS diary_ad AFTER DELETE ON DiarySegment BEGIN
  INSERT INTO DiaryFts(DiaryFts, rowid, text) VALUES ('delete', old.rowid, old.text);
END;
CREATE TRIGGER IF NOT EXISTS diary_au AFTER UPDATE ON DiarySegment BEGIN
  INSERT INTO DiaryFts(DiaryFts, rowid, text) VALUES ('delete', old.rowid, old.text);
  INSERT INTO DiaryFts(rowid, text) VALUES (new.rowid, new.text);
END;
