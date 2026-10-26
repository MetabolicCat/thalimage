# Organization review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

18 findings: 4 medium, 14 low. Covered backend `src/` and `tests/`, frontend
`src/`, build, CI and Docker config, and the Emacs dev helpers: dead code and
unused symbols in both languages, duplicated logic and constants, import
cycles, vestigial schema columns, oversized modules. No leftover debug code,
no commented-out code, no unused dependencies, components or TS types.

## ORG-001: Break the service import cycles instead of hiding them in local imports

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:257`, `backend/src/thalimage/services/scan_service.py:280`, `backend/src/thalimage/services/scan_service.py:370-379`, `backend/src/thalimage/services/file_deletion.py:14`, `backend/src/thalimage/services/file_renaming.py:17`, `backend/src/thalimage/services/picture_edits.py:99-102`, `backend/src/thalimage/services/identity.py:7`
- **Labels:** organization, backend

Two cycles are kept alive only by function-local imports: `scan_service` →
(local, line 280) `file_renaming` → `file_deletion` → `scan_service` (the file
modules import the 600-line orchestrator just for `unchanged_since_scan` and
`_iso`); and `picture_edits` → (local, line 102, with a comment on the cycle)
`identity` → `elo_service` (for `replay_scores`) → `image_service` →
`picture_edits`. `scan_service.py:257` also imports `collection_service`
locally with no cycle at all.

**Why it matters:** the dependency direction is hidden, any new top-level
import on these paths becomes an ImportError at startup, and a small
predicate drags the whole scan module into file deletion.

**Suggested fix:** move `unchanged_since_scan`/`_iso` to a leaf module (e.g.
`services/file_changes.py`), move `replay_scores`/`_after_match` (with
`START_SCORE`, `K_FACTOR`) to a scoring module not importing `image_service`,
then hoist the three local imports.

**Done when:** `scan_service`, `file_renaming`, `picture_edits` and
`collection_service` are imported only at module top level, and
`python -c "import thalimage.services.file_deletion"` does not load
`thalimage.services.scan_service`.

## ORG-002: Share the "changed since scan" guard between file deletion and renaming

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/file_deletion.py:43-54`, `backend/src/thalimage/services/file_deletion.py:150-157`, `backend/src/thalimage/services/file_renaming.py:33-51`, `backend/src/thalimage/services/file_renaming.py:105-113`
- **Labels:** organization, backend

Both modules define the same `_LOCATION` query, near-identical target
dataclasses (`_Target`, `_Copy`), and the same refusal: stat the file, treat
`FileNotFoundError` as changed, call `unchanged_since_scan`, refuse with
"changed since the last scan; rescan first."

**Why it matters:** the check that keeps disk changes off files the index no
longer describes exists twice and can drift.

**Suggested fix:** one helper, e.g. `still_as_scanned(conn, source_id, root,
path) -> bool`, with the query, next to `writable_root` in `file_changes.py`,
used by `file_deletion._remove` and `file_renaming._refusal` (this also
removes the `scan_service` import of ORG-001).

**Done when:** the location query and the stat/compare logic appear once and
both modules call the helper.

## ORG-003: Encode collection membership once

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/collection_service.py:35-45`, `backend/src/thalimage/services/collection_service.py:52-70`, `backend/src/thalimage/services/elo_ranking.py:21-30`, `backend/src/thalimage/services/elo_service.py:55-66`, `backend/src/thalimage/services/elo_service.py:205-227`
- **Labels:** organization, backend

"A source preset holds its source's images, any other collection its
`collection_images` rows" is written five times: `resolve_scope` (Python),
the `members` CTE in `_COUNT_SQL` (SQL `UNION`), `member_sql` (SQL `CASE`),
`get_pair` (branching), and `_in_collection` (branching plus two queries),
which could be one query using `member_sql("c", "?")` from a module
`elo_service` already imports.

**Why it matters:** a change to what a collection contains has to be made in
five differently-shaped places.

**Suggested fix:** make `member_sql` (or a `members_sql(collection_id)`
subquery) the single definition used by `_in_collection`, the `get_pair` pool
and `_COUNT_SQL`; keep `resolve_scope` for listing filters only.

**Done when:** `rg "source_preset" backend/src/thalimage/services` shows
membership logic only in the shared helper, plus creation and constraint code.

## ORG-004: Split the 1025-line viewer page

- **Severity:** medium
- **Confidence:** medium
- **Location:** `frontend/src/routes/image/[hash]/+page.svelte:76-226`, `frontend/src/routes/image/[hash]/+page.svelte:228-260`, `frontend/src/routes/image/[hash]/+page.svelte:430-515`
- **Labels:** organization, frontend

One component with ~20 `$state` variables and 13 `$effect`s mixes the
neighbour-window cache (`WINDOW`/`WINDOW_EDGE`, `windowCovers`,
`refreshWindow`, `navigate`), slideshow entry, video controls, top bar and
bottom sheet, and the archive, possible-edit, rename and delete dialogs.
CLAUDE.md says page state lives in unit-tested lib modules; the windowing
logic, the most intricate part, lives in the route untested.

**Why it matters:** prev/next edge cases can be exercised only through the
whole page, and every change touches one very large file.

**Suggested fix:** extract the neighbour window into
`lib/viewerWindow.svelte.ts` (a class like `Gallery`) with a test; optionally
move rename/delete flows into a component beside `DeleteDialog`.

**Done when:** the windowing logic lives in a lib module with vitest coverage
and the route only wires it to navigation.

See also: TST-002 (the test gap this leaves).

## ORG-005: Use one SHA-256 file hasher

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/hasher.py:9-15`, `backend/src/thalimage/core/sidecars.py:44-50`
- **Labels:** organization, backend

`hasher.content_hash` and `sidecars.digest` are the same function (SHA-256 of
the whole file in 64 KiB chunks); `scan_service` imports both (lines 17, 22).

**Why it matters:** duplicate code for one primitive, with names that suggest
a difference that does not exist.

**Suggested fix:** delete `sidecars.digest` and use `hasher.content_hash` in
`scan_service`, `file_renaming` and `source_summary`.

**Done when:** only one function in `core/` hashes a whole file.

## ORG-006: Derive the stored video format in one place

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/scan_service.py:406`, `backend/src/thalimage/services/image_service.py:117-118`, `backend/src/thalimage/services/playable_copies.py:19-20`, `frontend/src/lib/media.ts:1-8`
- **Labels:** organization, backend, frontend

"A video's `format` is its upper-cased extension" is computed separately by
the scanner (`suffix.lstrip(".").upper()`), `image_service.VIDEO_FORMATS` (a
set) and `playable_copies._VIDEO_FORMATS` (a quoted SQL list). The frontend
keeps a hand-copied extension list ("must match VIDEO_EXTENSIONS in backend
core/video.py") and classifies by filename in five components, though every
summary already carries `format`.

**Why it matters:** adding a container means editing several lists in two
languages that must agree.

**Suggested fix:** `VIDEO_FORMATS` and `video_format(path)` in `core/video.py`
for the three backend sites; optionally expose `is_video`/`media_type` on
`ImageSummary`/`SequenceItem` and drop `media.ts`.

**Done when:** the mapping is written once in the backend and the frontend
keeps no extension list (or a test asserts the two match).

## ORG-007: Merge the two ffprobe wrappers

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/video.py:29-58`, `backend/src/thalimage/core/video.py:119-130`
- **Labels:** organization, backend

`extract_video_info` and `probe_streams` each run `ffprobe … -show_streams`
with JSON output and a 30 s timeout and raise the same "ffprobe failed for …"
error. `extract_video_info` also returns a `"codec"` key nothing reads.

**Why it matters:** two subprocess call sites to keep consistent for one probe.

**Suggested fix:** build `extract_video_info` on `probe_streams` (first video
stream, skipping attached pictures as `playable_copy_args` does); drop
`codec`.

**Done when:** `core/video.py` invokes `ffprobe` in one function.

## ORG-008: Drop vestigial columns `sources.enabled` and `images.thumb_generated`

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/db/migrations/001_initial.sql:7`, `backend/src/thalimage/db/migrations/001_initial.sql:25`, `backend/src/thalimage/api/sources.py:89`, `backend/src/thalimage/api/sources.py:121`, `backend/src/thalimage/services/scan_service.py:491-499`, `backend/src/thalimage/services/image_service.py:36`, `frontend/src/lib/types.ts:10`, `frontend/src/lib/types.ts:110`
- **Labels:** organization, backend, frontend

`sources.enabled` is only ever set to 1 and nothing filters on or reads it.
`images.thumb_generated` is set to 1 on every upsert and shipped in every
`ImageSummary`, but nothing outside tests and fixtures reads it.

**Why it matters:** they suggest features (disabling a source, tracking
pending thumbnails) that don't exist and weigh down every listing payload.

**Suggested fix:** remove both from the response models and TS types, stop
writing `thumb_generated`; dropping the columns is optional.

**Done when:** neither field appears in API responses or `types.ts`, and the
gate passes.

## ORG-009: Remove the test-only `list_images` wrapper

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:338-377`
- **Labels:** organization, backend

No production code calls `list_images` (the API uses `listing_page`,
`api/images.py:143`); only three test modules do. It rebuilds `ListingFilters`
field by field and has fallen behind: it cannot pass `archived`,
`possible_edits` or `near_duplicates`.

**Why it matters:** a second entry point into the listing that must track
every new filter, and already doesn't.

**Suggested fix:** delete it, have the tests call `listing_page(db,
ListingFilters(...))`, and update the docstring that points at it.

**Done when:** `list_images` is gone and the tests use `listing_page`.

## ORG-010: Remove dead code in `api.ts`, `ScanManager` and `_page`

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/api.ts:211-213`, `backend/src/thalimage/services/scan_manager.py:4`, `backend/src/thalimage/services/scan_manager.py:33`, `backend/src/thalimage/services/image_service.py:404-405`
- **Labels:** organization, backend, frontend

`imageFileUrl` is exported and used nowhere; `ScanManager._global_lock` is
created (the module's only use of `threading`) and never acquired; `_page`'s
`direction not in ("asc", "desc")` normalization cannot trigger, since both
callers pass a direction normalized by `_ordering` (line 312) or its reverse.

**Why it matters:** dead code misleads, and the unused lock suggests thread
safety that isn't there.

**Suggested fix:** delete all three and the `threading` import.

**Done when:** none of the three remains and the gate passes.

## ORG-011: Use `copyPath` and one failure formatter everywhere

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/lib/imageCopies.ts:4-6`, `frontend/src/routes/review/+page.svelte:74-77`, `frontend/src/lib/comparison.ts:66`, `frontend/src/lib/imageCopies.ts:24-30`, `frontend/src/routes/review/+page.svelte:93-95`
- **Labels:** organization, frontend

`copyPath` joins `source_path` and `relative_path` with `/\/+$/`; the review
page (`filesOf`) and `comparison.ts` inline the join with `/\/$/`. The review
page also has its own `failures()` formatter beside `deletionFailures`.

**Why it matters:** the three copies already differ in how many trailing
slashes they strip.

**Suggested fix:** call `copyPath` in both places; add a list-returning
variant next to `deletionFailures` for the review page.

**Done when:** `rg "source_path.replace" frontend/src` matches only
`imageCopies.ts`.

## ORG-012: Move the shared grid-page glue into `Gallery`

- **Severity:** low
- **Confidence:** medium
- **Location:** `frontend/src/routes/+page.svelte:29-95`, `frontend/src/routes/collections/[id]/+page.svelte:33-107`
- **Labels:** organization, frontend

Both grid pages repeat the `beforeNavigate` → `saveScrollPosition` hook and
`restoredScrollTop`/`currentScrollTop` pair, the `show_nsfw` refetch
`$effect`, and an `onFilterChange` that stores filters, calls
`rememberContext()` and resets the gallery; they build storage keys
differently (a local `galleryKey` vs `collectionFiltersKey` exported from
`gallery.svelte.ts`).

**Why it matters:** behaviour changes to grid pages must be made twice.

**Suggested fix:** move scroll save/restore, the NSFW refresh and filter
persistence into `Gallery`, with both key builders in `gallery.svelte.ts`.

**Done when:** the shared effects exist once, in `gallery.svelte.ts`, with
tests.

## ORG-013: Share the `settings` key/value encoding

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/user_settings.py:18-52`, `backend/src/thalimage/services/db_backup.py:58-108`
- **Labels:** organization, backend

Both modules store typed values in `settings` with the same hand-written
encoding (bool as `"true"`/`"false"`, numbers via `str`) and the same upsert
SQL, which appears three times (`user_settings.py:48`, `db_backup.py:89`,
`:104`), each with its own decoding loop.

**Why it matters:** each new setting copies the pattern again, and the copies
already differ (one validates through pydantic).

**Suggested fix:** `read_settings(conn, keys)`/`write_settings(conn, values)`
helpers used by both, with pydantic doing the coercion.

**Done when:** the `INSERT INTO settings ... ON CONFLICT` statement appears once.

## ORG-014: Name the duplicated constants once

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/image_service.py:247-253`, `backend/src/thalimage/services/elo_service.py:21`, `frontend/src/lib/slideshowStore.svelte.ts:103`, `backend/src/thalimage/api/images.py:58`, `backend/src/thalimage/app.py:31`
- **Labels:** organization, backend

The ELO start score is `START_SCORE = 1500.0` in `elo_service`, hardcoded as
`1500.0` in `image_service._ELO_SCORE_SQL` (ORG-001's cycle prevents the
import) and again as `1500` in the frontend slideshow. The immutable cache
header is written in both `app.py` (`IMMUTABLE_CACHE`) and `api/images.py`
(`IMMUTABLE`).

**Why it matters:** changing either silently splits behaviour (ELO sorting vs
voting).

**Suggested fix:** bind `START_SCORE` into `_ELO_SCORE_SQL` after ORG-001;
have `sequence()` return the defaulted score; define the header once.

**Done when:** each value is a literal in exactly one backend place.

## ORG-015: Trim `ImageFileInfo` to what the scan uses

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/core/metadata.py:16-24`, `backend/src/thalimage/core/metadata.py:71-83`, `backend/src/thalimage/services/scan_service.py:364-367`
- **Labels:** organization, backend

`_extract_file_info` stats the file to fill `filename`, `file_size`,
`modified` and `created`, which the scan never reads (it uses only `width`,
`height`, `aspect_ratio`, `format`, `scan_service.py:412-414`, and takes size,
mtime and birth time from its own `stat`). Birth time is read both in
`metadata.py:82` and `scan_service._birthtime`; only `test_metadata.py:17`
reads one of the fields.

**Why it matters:** a redundant stat, and data that looks authoritative but is
ignored.

**Suggested fix:** reduce `ImageFileInfo` to `format`, `width`, `height`,
`aspect_ratio`, drop the stat, adjust the one test.

**Done when:** `metadata.py` no longer calls `stat()`.

## ORG-016: Reuse `_record_sql` in `image_standings`

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/elo_service.py:251-256`, `backend/src/thalimage/services/elo_service.py:334-337`
- **Labels:** organization, backend

`_record_sql` builds the wins/losses subqueries with the collection hardcoded
as `?`, so `image_standings` writes them out again with `e.collection_id`.

**Why it matters:** the definition of a win or loss exists twice.

**Suggested fix:** give `_record_sql` a `collection` argument (as `ranked_sql`
has, default `"?"`) and call it from both.

**Done when:** `votes v WHERE ... winner_hash` appears once in `elo_service.py`.

## ORG-017: Raise the pydantic-settings floor and drop the TOML import fallback

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/config.py:11-14`, `backend/src/thalimage/config.py:35-46`, `backend/pyproject.toml:22`
- **Labels:** organization, backend

`config.py` wraps `from pydantic_settings import TomlConfigSettingsSource` in
`try/except ImportError` and silently ignores `config.toml` when it fails,
only because the floor is `pydantic-settings>=2.0.0`. The lock resolves 2.13.1
(`uv.lock:671`); the TOML source has shipped since 2.2 to the reviewer's
recollection (not checked against release notes).

**Why it matters:** a dead branch that, if ever taken, would drop a documented
config file without warning.

**Suggested fix:** require `pydantic-settings>=2.2` (after confirming the
version in the changelog) and import unconditionally.

**Done when:** the `try/except` and the `is not None` branch are gone and the
floor is raised.

## ORG-018: Drop unused parameters and single-use indirection

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/locations.py:19-24`, `backend/src/thalimage/services/folders.py:24-31`, `frontend/src/routes/image/[hash]/+page.svelte:183-185`, `frontend/src/lib/stores.ts:5-20`, `frontend/src/lib/mobileStore.svelte.ts:21-36`
- **Labels:** organization, backend, frontend

`in_source_sql`'s `source_param`/`hash_col` and `in_folder_sql`'s `hash_col`
are never passed (one call each, `image_service.py:191`, `:206`); the viewer's
`setIndex(idx)` is just `currentIndex = idx`; `createDataStore<T>` is a
generic factory with one user (`collectionsStore`); `responsiveThumbSize` is
grid layout code in the mobile drawer store that repeats ImageGrid's
`gap = 8` (`ImageGrid.svelte:12`) as `GRID_GAP`.

**Why it matters:** parameters and abstractions with no second use send
readers looking for variants that don't exist; the copied gap can drift.

**Suggested fix:** remove the unused parameters, inline `setIndex` and
`createDataStore`, move `responsiveThumbSize` next to the grid sharing one
gap constant.

**Done when:** none of these indirections remain and the grid gap is defined
once.
