-- Scene shared stashes (group inventory mirrors, docs/03 GS-*)

ALTER TABLE Scene ADD COLUMN sharedStashJson TEXT NOT NULL DEFAULT '{}';
