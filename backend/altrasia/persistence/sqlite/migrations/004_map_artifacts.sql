-- MAP-1 / MAP-11: per-scene and world map artifacts (Phase 6 depth)
CREATE TABLE IF NOT EXISTS MapArtifact (
  artifactId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL,
  sceneId TEXT,
  kind TEXT NOT NULL DEFAULT 'floor',
  version INTEGER NOT NULL DEFAULT 1,
  jsonBlob TEXT NOT NULL,
  createdAt TEXT NOT NULL,
  FOREIGN KEY (worldId) REFERENCES World(worldId)
);

CREATE INDEX IF NOT EXISTS idx_map_artifact_world ON MapArtifact(worldId);
CREATE INDEX IF NOT EXISTS idx_map_artifact_scene ON MapArtifact(worldId, sceneId);

CREATE TABLE IF NOT EXISTS MediaAsset (
  assetId TEXT PRIMARY KEY,
  worldId TEXT NOT NULL,
  characterId TEXT,
  path TEXT,
  sha256 TEXT,
  workflowId TEXT,
  sourceJobId TEXT,
  createdAt TEXT NOT NULL,
  FOREIGN KEY (worldId) REFERENCES World(worldId)
);
