# General review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

10 findings: 1 high, 4 medium, 5 low. GEN-001, 002, 004, 005, 007 and 009
were reproduced or measured with throwaway scripts outside the repo; the rest
are from reading the code, with the evidence cited.

## GEN-001: Perceptual hash pads at full resolution, memory grows with max(w,h)²

- **Severity:** high
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/perceptual_hash.py:37-42`, `backend/src/thalimage/services/scan_service.py:415`
- **Labels:** bug, performance, area:scan

Since #158 (ae7f2b7) `perceptual_hash` builds a white RGBA square whose side
is the picture's long edge, at full resolution, before shrinking it to 32x32
(`side = max(rgba.size)`, `Image.new("RGBA", (side, side))`). Memory now grows
with the square of the long edge rather than the pixel count: an 800x12000
PNG measured 778 MB peak RSS against 43 MB for 1024x1024. Pillow's bomb limit
counts w*h, so a 1500x59000 strip opens and then asks for about 14 GB.

**Why it matters:** one tall or wide picture (webtoon strip, panorama) can
OOM-kill the container mid-scan; `PERCEPTUAL_HASH_VERSION = 3` makes the next
scan hash every picture, and scans run concurrently by default.

**Suggested fix:** shrink before padding (`thumbnail`/`reduce` to a bounded
long edge, ~512-1024 px), pad that onto a square, resize to 32x32. Raise
`PERCEPTUAL_HASH_VERSION` if values move, after GEN-004 is fixed.

**Done when:** hashing an 800x12000 picture stays under about 100 MB peak, and
a test asserts tall and wide pictures hash without a full-size square.

**Details:** [details/GEN-001.md](details/GEN-001.md)

## GEN-002: Removing a source while it is scanned brings its images and preset back

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/sources.py:172-184`, `backend/src/thalimage/api/sources.py:245-275`, `backend/src/thalimage/services/scan_service.py:198-260`, `backend/src/thalimage/services/source_service.py:29-89`, `frontend/src/routes/settings/+page.svelte:87-97`
- **Labels:** bug, concurrency, area:sources

`DELETE /sources/{id}` never checks `scan_manager.is_running`, and Settings
offers Remove during a scan. The worker keeps going: later batches insert
`image_locations` for the removed source, `sync_images` sets `deleted = 0`,
and `get_or_create_source_preset` re-creates its preset. Reproduced with
`keep_data=True`: `removed_at` set, yet 2 live images, 2 locations and a new
`source_preset` row. With `keep_data=false` later batches hit the `sources`
foreign key and the scan fails.

**Why it matters:** a removed source's images reappear in All Images, and an
undeletable preset for a source no longer in Settings appears in the sidebar.

**Suggested fix:** refuse removal with 409 while
`scan_manager.is_running(source_id)` (and disable Remove in the UI), or have
the scan check `removed_at` before each batch and before the preset, and abort.

**Done when:** a test removing a source during a scan ends with no live
locations and no preset for it, or the removal is refused with 409.

**Details:** [details/GEN-002.md](details/GEN-002.md)

## GEN-003: Labelling page treats imported star ratings as labels and deletes them

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/lib/labels.ts:47`, `frontend/src/lib/labels.ts:56-64`, `backend/src/thalimage/services/tag_service.py:141-162`, `backend/src/thalimage/services/scan_service.py:529`
- **Labels:** bug, data-loss, area:tags

The label vocabulary's single-valued `rating` namespace (`rating:sfw` …
`rating:porn`) shares its prefix with the tags a scan imports from file star
ratings (`rating:1` … `rating:5`). `collection_labels` returns `rating:3` as a
label, so `missingNamespaces` counts the image rated and "Next unlabelled"
skips it. Clicking `rating:sfw` removes every other `rating:` tag
(`toggleLabel` returns `remove: sameNamespace`), deleting `rating:3`, which
`images.file_tags` then prevents from being re-imported ("Removing such a tag
in Thalimage is final", `docs/04-scanning.md:33`).

**Why it matters:** labelling silently and permanently destroys imported star
ratings, and reports wrong progress.

**Suggested fix:** a non-colliding namespace (e.g. `content-rating:`), or
restrict `collection_labels` and `toggleLabel` to the vocabulary's values.

**Done when:** labelling an image carrying `rating:3` leaves that tag in place
and still reports the rating namespace as missing.

## GEN-004: Raising the perceptual-hash version re-reads every video

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:166-174`, `backend/src/thalimage/services/scan_service.py:188-191`, `backend/src/thalimage/services/scan_service.py:503-505`, `backend/src/thalimage/db/migrations/025_perceptual_hash.sql:5-6`
- **Labels:** bug, performance, area:scan

Videos have no perceptual hash, but `_upsert_image` stamps them with the
current `PERCEPTUAL_HASH_VERSION` and the skip test requires
`perceptual_hash_version >= PERCEPTUAL_HASH_VERSION` for every file, so each
bump (2 → 3 in ae7f2b7) sends every unchanged video through `_index_file`
again: picture hash, full-file SHA-256 and ffprobe. Migration 025 says the
opposite ("Videos get no perceptual hash, so they are current already").
Without ffmpeg the re-read raises `_SkipFile`, the location is dropped and the
video marked deleted. Reproduced: a video at version 3 is skipped; at version
2 the scan ends `errors=1, deleted=1`.

**Why it matters:** each perceptual-hash change costs two full reads of every
video over the NAS, and hides every video when ffmpeg is missing.

**Suggested fix:** exempt videos from the perceptual-version test; separately
keep the location of a previously indexed file that hits `_SkipFile`, as for
other read errors.

**Done when:** a scan after raising `PERCEPTUAL_HASH_VERSION` reports
unchanged videos as skipped, and a known video is not marked deleted when
ffmpeg is unavailable.

## GEN-005: Source summary lists a folder once per duplicate copy

- **Severity:** medium
- **Confidence:** medium
- **Location:** `backend/src/thalimage/services/source_summary.py:82`, `backend/src/thalimage/services/source_summary.py:118-130`, `backend/src/thalimage/core/sidecars.py:15-27`, `frontend/src/routes/settings/+page.svelte:32-36`
- **Labels:** performance, area:sources

For each path of every duplicate group, `_sidecars` calls `sidecars_of`, which
lists the whole folder (`media.parent.iterdir()`), then reads every sidecar
found in full (`digest`): O(duplicate paths × folder size). Measured on local
disk: 1000 paths in a 5000-file folder took 11.9 s. Settings fetches every
source's summary on load and after each scan.

**Why it matters:** Settings takes seconds to minutes to load on a real
library over NFS.

**Suggested fix:** list each folder once (group paths by parent, or reuse the
`sidecars` table the scan keeps with digests) and match names in memory.

**Done when:** the summary of a source with 1000 duplicate paths in one
5000-file folder lists that folder once and returns in well under a second.

## GEN-006: Thumbnails and previews ignore EXIF orientation

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/thumbnails.py:34-36`, `backend/src/thalimage/core/previews.py:53-59`, `backend/src/thalimage/core/webp.py:15-27`, `backend/src/thalimage/core/metadata.py:78`
- **Labels:** bug, area:media

Nothing in the backend calls `ImageOps.exif_transpose` (no match for
`exif_transpose` or `Orientation`), and the WebP writer drops EXIF, so a JPEG
with an Orientation tag gets a sideways thumbnail and viewer preview; its
stored width, height and aspect ratio are the raw ones, skewing the grid and
the portrait/landscape filters. The original served by `/file` is rotated by
the browser.

**Why it matters:** phone photos and photo-app edits show rotated in the grid
and viewer.

**Suggested fix:** `ImageOps.exif_transpose` before `write_webp` and when
reading dimensions; bump `EXTRACTOR_VERSION` and drop affected cached
thumbnails.

**Done when:** a JPEG with Orientation 6 gets a portrait thumbnail and preview,
and stored width < height.

## GEN-007: Re-keying in a scan drops pending possible-edit questions

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:453-456`, `backend/src/thalimage/services/identity.py:21-59`, `backend/src/thalimage/services/picture_edits.py:104-107`
- **Labels:** bug, area:identity

`picture_edits` holds image keys with no foreign key, and only `merge_keys`
re-points them; the scan's re-keying on a `HASH_VERSION` bump calls
`rekey_image` directly, which does not. A pending pair (old, N) keeps
`new_hash = N` after N becomes N′ and N's row is deleted, so
`possible_edit_of(N′)` finds nothing and the possible-edits filter drops it.
Kept-separate decisions are orphaned the same way.

**Why it matters:** after a re-keying scan, undecided edits silently vanish.

**Suggested fix:** re-point `picture_edits` in `rekey_image` (both columns,
`UPDATE OR IGNORE`, then delete leftovers).

**Done when:** a test with a pending edit, then a scan with a raised
`HASH_VERSION`, still offers the edit on the new key.

## GEN-008: Derived files of merged or purged images stay in the cache forever

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/images.py:469-487`, `backend/src/thalimage/api/sources.py:181-184`, `backend/src/thalimage/api/images.py:358-360`
- **Labels:** bug, resource-leak, area:media

Merging deletes the merged image's row (`rekey_image` → `DELETE FROM images`)
but `merge_into_image` removes only its playable copy, leaving its thumbnail
and up to three previews. `del_source(keep_data=false)` likewise removes only
playable copies of the images it purges. The possible-edit merge does call
`remove_derived` for the retired key, so the three paths disagree.

**Why it matters:** orphaned WebP files accumulate in `cache/` with no way to
clean them up.

**Suggested fix:** call `remove_derived(DerivedDirs(...), key)` for each
merged key and purged image, as `decide_possible_edit` does.

**Done when:** after a merge and after removing a source without its data, no
thumbnail, preview or video copy remains under the retired keys.

## GEN-009: Picture hash raises IndexError on JPEGs cut between segments

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/picture_hash.py:54`, `backend/src/thalimage/core/picture_hash.py:114-122`, `backend/tests/test_picture_hash.py:61-65`
- **Labels:** bug, area:identity

The module promises that any file "whose structure does not hold together
falls back to the whole-file hash", but `_jpeg` indexes the mmap
(`data[off]`, `data[off + 1]`) without bounds checks and `picture_hash`
catches only `_Malformed`, `ValueError` and `struct.error`. A JPEG ending after
SOI, after a complete segment, or on a fill byte raises `IndexError: mmap
index out of range` (reproduced with `ffd8`, `ffd8ff`, `ffd8ffff`,
`ffd8ffe00004ab` and a real JPEG cut after each of its first three segments);
a scan records that as the failure reason. The only truncation test cuts at
`len(data) // 3`, which lands in scan data and raises `_Malformed`.

**Why it matters:** an internal error instead of the documented fallback;
small impact, since Pillow cannot open these files either.

**Suggested fix:** catch `IndexError` too (or bounds-check `off` in `_jpeg`),
and parametrize the truncation test over every segment boundary of each
fixture.

**Done when:** `picture_hash` returns `content_hash(path)` for a JPEG cut at
every segment boundary.

## GEN-010: Label page says "no images" while loading, and desyncs after a failed toggle

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/routes/label/[collectionId]/+page.svelte:76-91`, `frontend/src/routes/label/[collectionId]/+page.svelte:176-178`
- **Labels:** bug, area:frontend

1. `current` is undefined only while `images` is empty, so the
   `images.length ? 'Loading…' : …` branch never shows "Loading…": "This
   collection has no images." shows until the request returns.
2. `toggle` removes tags one by one, then adds; if a later request fails, the
   tags already removed server-side stay in `image.labels`, the next click on
   them gets a 404 ("Tag not found on image"), and the page stays wrong until
   reloaded. A 409 from `createTag` (created in another tab) fails the same way.

**Why it matters:** misleading empty state on large collections, stuck label
state after a transient error.

**Suggested fix:** a `loaded` flag for the status text; after an error in
`toggle`, re-read that image's tags; on 409, look the tag up again.

**Done when:** the page shows "Loading…" until the first response, and a
toggle failing halfway leaves the buttons matching the server.
