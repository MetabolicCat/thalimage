# Docs consistency review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

12 findings: 3 medium, 9 low. The in-app user docs held up well: every
spot-checked number (K=32, start 1500, the opponent spread, slideshow odds and
cooldown, preview sizes, thresholds, batch sizes, backup defaults, ignored
files, the 256 KiB sidecar limit), UI label and key binding matched the code.
The drift is mostly in contributor and operator docs.

## Inventory

| File | Class | Reason |
|---|---|---|
| `README.md` | current | Features, deployment, configuration, development commands |
| `CLAUDE.md` | current | Contributor layout and conventions |
| `docs/design.md` | current (one section is a plan) | "Decisions the code follows"; the "Image analysis" section records decisions for unbuilt code (DOC-003) |
| `backend/src/thalimage/docs/01-overview.md` | current | In-app user docs: core data model |
| `backend/src/thalimage/docs/02-elo.md` | current | In-app user docs: voting, rankings, stats, weighted slideshow |
| `backend/src/thalimage/docs/03-delivery.md` | current | In-app user docs: thumbnails, previews, video |
| `backend/src/thalimage/docs/04-scanning.md` | current | In-app user docs: scanning, identity, sidecars, renaming, removal |
| `backend/src/thalimage/docs/05-selecting.md` | current | In-app user docs: selection bar and group review |
| `docs/archive/README.md` | historical | Index of archived records |
| `docs/archive/mvp-plan.md` | historical | Archived MVP plan (banner) |
| `docs/archive/reboot.org` | historical | Archived original vision notes (banner) |
| `docs/archive/roadmap.md` | historical | Roadmap archived 2026-10-16 (banner) |
| `docs/archive/todos.md` | historical | Fix log, all resolved (banner) |
| `docs/archive/reviews/2026-04-cr_1.md` | historical | Dated code-review record (banner) |
| `docs/archive/reviews/2026-06.md` | historical | Dated remediation log (banner) |
| `docs/archive/reviews/2026-07.md` | historical | Dated review record (banner) |
| `docker/docker-compose.yml` (comments) | current | Operator docs embedded in the sample stack |
| `docker/.env.example` (comments) | current | Operator docs for each variable |
| `backend/pyproject.toml` (`description`) | current | Packaging metadata; matches the README |
| `thalimage-dev.el` (commentary) | current | Describes the Emacs dev commands |
| `docs/review/**` | out of scope | Earlier review runs |

Not documentation: `LICENSE`, `frontend/static/robots.txt`.

Organization is sound: every archive file carries an *Archived* banner and is
indexed in `docs/archive/README.md`, the README "Documentation" section is the
entry point, and current and historical material is mixed only inside
`docs/design.md` (DOC-003). No layout change is needed. No text addressed to
AI agents was found.

## DOC-001: State in README Security that the open API can delete files on disk

- **Severity:** medium
- **Confidence:** high
- **Location:** `README.md:50-55`, `backend/src/thalimage/api/images.py:426`, `backend/src/thalimage/api/images.py:445`, `backend/src/thalimage/api/images.py:469`, `backend/src/thalimage/api/images.py:507`, `backend/src/thalimage/api/sources.py:143-163`
- **Labels:** documentation, area:deployment, security

The Security section lists what an unauthenticated caller can do ("add and
delete sources, trigger scans, archive images, edit tags and delete
collections", stream originals) but leaves out the most destructive: deleting
image files and sidecars (`POST /images/{hash}/delete`, `POST
/images/delete`), merging (which deletes files), renaming, and marking a
source writable (`PATCH /sources/{id}`, which needs only a test write).

**Why it matters:** an operator could judge a mount that accepts writes safe;
anyone reaching the port can then delete originals.

**Suggested fix:** add that callers can mark sources writable and then delete,
rename or merge files in them, and keep the `:ro` mounts as the defence.

**Done when:** README Security names the file delete, rename and merge actions
and the writable toggle, and points to `:ro` mounts.

See also: SEC-001 (a delete path that escapes the writable gate entirely).

## DOC-002: Document the indexed image formats; HEIC is named but never indexed

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/docs/04-scanning.md:19-25`, `backend/src/thalimage/core/scanner.py:10-12`, `backend/src/thalimage/core/picture_hash.py:13`, `README.md:7`
- **Labels:** documentation, area:scan

The scanning page says "JPEG, PNG, WebP, TIFF, AVIF/HEIC, MP4 and MOV files
are read this way", but the scanner indexes only `.jpg .jpeg .png .gif .bmp
.tiff .webp .avif` plus video extensions: `.heic`/`.heif` and `.tif` files are
never indexed and show up as "Orphan files" (04-scanning.md:206-210). No
current doc lists the indexed image extensions (the README lists videos only,
`README.md:16`).

**Why it matters:** users told HEIC is handled cannot see why their `.heic` or
`.tif` files are missing.

**Suggested fix:** list the indexed extensions in 04-scanning.md and the
README features; mention HEIC only as a hash parser detail, or drop it.

**Done when:** the user docs list exactly `SUPPORTED_EXTENSIONS`, and none
implies `.heic` or `.tif` is indexed.

## DOC-003: Separate the unbuilt "Image analysis" plan from current design decisions

- **Severity:** medium
- **Confidence:** high
- **Location:** `docs/design.md:3`, `docs/design.md:130-166`, `docs/design.md:97-109`, `docs/design.md:91-96`
- **Labels:** documentation, area:ai

`design.md` presents itself as "Decisions the code follows" (line 3), but its
"Image analysis" section records #164 decisions for auto-tagging that is not
built (no embedding or worker code; no DINOv2, SigLIP or linkage in `src`),
partly in the present tense, and one contradicts the code: line 151 says
"Groups are formed by complete linkage" with "a merge tree … the slider only
cuts it", while lines 97-109 and `services/near_duplicates.py` describe the
grouping in use (around a start, not chained). Lines 141-145 repeat the #158
padding result of lines 91-96.

**Why it matters:** a contributor cannot tell which grouping rule the code
follows, and may "fix" correct code.

**Suggested fix:** move the section under a "Planned (#126/#164)" heading or
into its own doc, saying it is not built; drop the repeated paragraph.

**Done when:** no sentence in `design.md` describes absent behaviour without
being marked planned, and near-duplicate grouping is described one way only.

## DOC-004: Bring the CLAUDE.md code layout up to date

- **Severity:** low
- **Confidence:** high
- **Location:** `CLAUDE.md:27-32`, `CLAUDE.md:38-42`
- **Labels:** documentation, area:contributing

The layout reads as a full inventory but omits: from `core/`, `picture_hash`
(the image identity), `perceptual_hash`, `sidecars`, `derived_files`; from
`services/`, 13 of 23 modules (`merging`, `near_duplicates`, `picture_edits`,
`identity`, `file_deletion`, `file_renaming`, `file_changes`, `db_backup`,
`playable_copies`, `source_summary`, `folders`, `elo_ranking`, `elo_stats`);
from `routes/`, `collections` (index), `collections/[id]/rankings`, `review`,
`label/[collectionId]`; and the page-state modules `review.svelte.ts` and
`imageSelection.svelte.ts`.

**Why it matters:** CLAUDE.md is the contributor map; identity, merging and
near-duplicates cannot be found from it.

**Suggested fix:** add the missing modules and routes with one-phrase roles,
or say the list shows entry points only.

**Done when:** every directory listed under `core/`, `services/` and `routes/`
matches disk, or the text says it is a selection.

## DOC-005: Document the Label page linked from every collection

- **Severity:** low
- **Confidence:** high
- **Location:** `frontend/src/routes/label/[collectionId]/+page.svelte:25-27`, `frontend/src/routes/collections/[id]/+page.svelte:141`, `frontend/src/routes/collections/[id]/+page.svelte:159`, `frontend/src/lib/labels.ts:1-4`, `frontend/src/lib/labels.ts:17-40`
- **Labels:** documentation, area:tags

Every collection shows a **Label** link to a page that tags images with a
fixed vocabulary of namespaced global tags (`medium:…`, `style:…`,
`overlay:…`) to measure the auto-tagging models (#164). Neither the in-app
docs, the README features nor the CLAUDE.md routes mention it.

**Why it matters:** users meet an unexplained control that creates global tags
they then see everywhere.

**Suggested fix:** a short "Labelling" section in the in-app docs (purpose,
vocabulary, labels are ordinary global tags), or hide the link if it is a
development tool.

**Done when:** the Label page's purpose and effect are described in `/docs`,
or the link is no longer shown to users.

See also: GEN-003 (its `rating` namespace collides with imported star ratings).

## DOC-006: Update the README feature list

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:5-19`, `README.md:278-283`
- **Labels:** documentation

The features list describes "date / aspect-ratio / media-type filters" and
leaves out the tag, archived, ELO, Edits and Alike filters, near-duplicate
groups and group review with merge, bulk selection, deleting and renaming
files in writable sources, possible-edit detection, daily database backups and
voting statistics, all covered by the in-app docs. Tech Stack omits ffmpeg.

**Why it matters:** the README undersells the app and omits that it can write
to files.

**Suggested fix:** one line per missing feature, and ffmpeg in Tech Stack.

**Done when:** every top-level feature with an in-app doc section is named in
the README features.

## DOC-007: List development prerequisites and the API explorer in README

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:246-276`, `CLAUDE.md:15`, `frontend/pnpm-workspace.yaml:1-3`, `backend/src/thalimage/app.py:77-85`, `backend/src/thalimage/docs/04-scanning.md:58-60`
- **Labels:** documentation, area:contributing

The Development section names uv and pnpm but not the versions `engineStrict`
enforces (Node 24, pnpm 10.28.0; only CLAUDE.md says so), nor ffmpeg (videos
are skipped and the video tests skip without it), nor how to get pnpm
(corepack). The OpenAPI explorer at `/api/docs` and `/api/redoc` is mentioned
nowhere.

**Why it matters:** a fresh setup fails at `pnpm install` on another Node, and
contributors don't know the API reference exists.

**Suggested fix:** a prerequisites line (Python 3.11+, uv, Node 24, pnpm via
corepack, ffmpeg/ffprobe optional for video) and a pointer to `/api/docs`.

**Done when:** the README Development section names each runtime with its
version and the API explorer URL.

## DOC-008: Correct the design.md wording on "All Images" and source presets

- **Severity:** low
- **Confidence:** high
- **Location:** `docs/design.md:11-15`, `frontend/src/lib/browsingContext.ts:6-24`, `backend/src/thalimage/services/image_service.py:190-192`, `backend/src/thalimage/db/migrations/013_image_locations.sql:1-8`
- **Labels:** documentation

design.md says "All Images" has "`id: null` in the browsing context"; the
context is `{ type: 'all', … }` with no id. It says presets are
`WHERE source_id = X`; they match any location of the image (`in_source_sql()`
over `image_locations`), since `images.source_id` is only the primary
location, so an image with copies in two sources lists in both presets.

**Why it matters:** preset queries written against `images.source_id` would
miss copies held in a second source.

**Suggested fix:** describe "All Images" as `type: 'all'` and presets as
images with a location in the source.

**Done when:** both bullets match `browsingContext.ts` and `in_source_sql()`.

## DOC-009: List cache/videos and near-duplicates.json in the storage descriptions

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:124-129`, `docker/.env.example:18-21`, `docker/docker-compose.yml:77`, `backend/src/thalimage/config.py:93-95`
- **Labels:** documentation, area:deployment

The README tree omits `cache/near-duplicates.json` (derived pairs written
after each change, read at startup); `.env.example` says `app/` holds
"cache/thumbs, cache/previews and db_backups/" without `cache/videos/`; the
compose comment says "Thumbnails, previews and the daily database backups"
without the video copies.

**Why it matters:** operators sizing or cleaning the share miss large
(`cache/videos`) or safely deletable derived files.

**Suggested fix:** add `cache/videos/` to `.env.example` and compose, and
`cache/near-duplicates.json` (derived, safe to delete) to the README tree.

**Done when:** the three descriptions list the same contents of `app/`,
matching `Settings.resolved_*`.

## DOC-010: Say the deploy secrets live in the test-deploy environment

- **Severity:** low
- **Confidence:** high
- **Location:** `README.md:36-38`, `.github/workflows/docker.yml:104-117`
- **Labels:** documentation, area:ci

The README says the redeploy uses "secrets `TS_OAUTH_ID`, `TS_AUDIENCE`,
`DEPLOY_WEBHOOK_URL`"; the workflow reads them from the `test-deploy`
environment, and the Tailscale trust credential must accept the subject
`…:environment:test-deploy` and the tag `tag:ci`. The README says neither.

**Why it matters:** repository-level secrets or a credential with another
subject make the deploy fail with nothing to explain why.

**Suggested fix:** name the `test-deploy` environment and the OIDC subject and
tag the credential must accept.

**Done when:** the README states where the secrets are defined and what the
Tailscale credential must accept.

## DOC-011: Fix the ci.yml comment on what check.sh runs

- **Severity:** low
- **Confidence:** high
- **Location:** `.github/workflows/ci.yml:59`, `check.sh:8-27`
- **Labels:** documentation, area:ci

The comment says the step runs "Lint, typecheck and tests for the backend,
then svelte-check"; `check.sh` also runs the lock check first and vitest last.

**Why it matters:** misleading when reading a CI failure, especially around
the lock check (PKG-001).

**Suggested fix:** "Lock check, lint, typecheck and tests for the backend,
then svelte-check and vitest".

**Done when:** the comment names every stage `check.sh` runs.

## DOC-012: Fix the `thalimage-dev.el` commentary for the frontend command

- **Severity:** low
- **Confidence:** high
- **Location:** `thalimage-dev.el:13`, `thalimage-dev.el:17`, `thalimage-dev.el:47-52`
- **Labels:** documentation, area:tooling

The commentary says `thalimage-dev-frontend` runs "frontend only ("make
fe-dev")" and `thalimage-dev-start` starts "backend + frontend dev servers";
the function runs `make fe-build && make fe-preview`, a production-like
preview without hot reload, as its own docstring says.

**Why it matters:** someone expecting the vite dev server gets a static build.

**Suggested fix:** correct the commentary; optionally rename the command
(e.g. `thalimage-dev-preview`) or add one for `make fe-dev`.

**Done when:** the commentary and the docstring describe the same command.
