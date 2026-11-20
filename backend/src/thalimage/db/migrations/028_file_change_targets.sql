-- A move changes files in two sources: `path` is relative to the one the
-- file left, `target` to the one it went to. Like source_id, the record
-- outlives the sources, so there is no foreign key.
ALTER TABLE file_changes ADD COLUMN target_source_id INTEGER;
