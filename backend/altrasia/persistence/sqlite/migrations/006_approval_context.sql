-- Altrasia migration 006: approval context for per-character web tools
ALTER TABLE Approval ADD COLUMN characterId TEXT;
ALTER TABLE Approval ADD COLUMN jobId TEXT;
ALTER TABLE Approval ADD COLUMN messageId TEXT;
ALTER TABLE Approval ADD COLUMN resultJson TEXT;
