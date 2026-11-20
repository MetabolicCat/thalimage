-- Whether a still image's file holds more than one frame, so the gallery can
-- offer an Animated category separately from still images. animation_version
-- records the detector that filled it: a scan reads an image whose version is
-- older again, even when the file is unchanged.
--
-- Only GIFs need that first re-read: they are the format an existing library
-- is likely to animate. Other formats are marked current; a new or changed
-- file of any format is still checked.
ALTER TABLE images ADD COLUMN animated BOOLEAN NOT NULL DEFAULT 0;
ALTER TABLE images ADD COLUMN animation_version INTEGER NOT NULL DEFAULT 0;

UPDATE images SET animation_version = 1
WHERE format != 'GIF';
