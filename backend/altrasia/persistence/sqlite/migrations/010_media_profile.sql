-- MediaAsset: record which image profile produced the asset
ALTER TABLE MediaAsset ADD COLUMN modelProfileId TEXT;
