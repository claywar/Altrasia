-- World-scoped character inventory (docs/03-locations-and-presence.md §4, LP-2)

ALTER TABLE WorldMember ADD COLUMN inventoryJson TEXT NOT NULL DEFAULT '{}';
