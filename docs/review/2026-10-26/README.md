# Full review: thalimage — 2026-10-26

- **Scope:** repository root, files tracked by git (`git ls-files`, 319 files,
  ~37k lines), excluding `docs/review/`.
- **Commit:** `4f48e65` (Merge pull request #171, certifi upgrade). **The
  working tree was dirty** in one line: for the duration of the review,
  `backend/pyproject.toml` carried an uncommitted
  `exclude-newer-package = { certifi = false }` under `[tool.uv]`, so that
  `./check.sh` (whose lock check fails at HEAD, see PKG-002) and `uv run`
  could run without rewriting `uv.lock`. Findings describe the committed
  state; the edit was reverted after the review.
- **Date:** 2026-10-26
- **Gate:** with that edit, `./check.sh` passed: 647 backend tests passed,
  18 skipped (ffmpeg absent locally; CI runs them, 665 passed), svelte-check
  0 errors, 205 frontend tests passed. Backend coverage (`make cov`): 92%.

## Counts

| Category | Critical | High | Medium | Low | Total |
|---|---|---|---|---|---|
| [Security](security.md) | 0 | 0 | 3 | 4 | 7 |
| [Organization](organization.md) | 0 | 0 | 4 | 14 | 18 |
| [Docs consistency](docs-consistency.md) | 0 | 0 | 3 | 9 | 12 |
| [Testing](testing.md) | 0 | 0 | 4 | 4 | 8 |
| [Packaging](packaging.md) | 0 | 1 | 2 | 5 | 8 |
| [General](general.md) | 0 | 1 | 4 | 5 | 10 |
| **Total** | **0** | **2** | **20** | **41** | **63** |

### High

- [PKG-001](packaging.md#pkg-001-stop-cis-make-install-rewriting-uvlock-before-the-lock-check): Stop CI's `make install` rewriting uv.lock before the lock check
- [GEN-001](general.md#gen-001-perceptual-hash-pads-at-full-resolution-memory-grows-with-maxwh²): Perceptual hash pads at full resolution, memory grows with max(w,h)²

### Medium

- [SEC-001](security.md#sec-001-unvalidated-hashes-in-post-imagesdelete-unlink-arbitrary-mp4-files): Unvalidated hashes in POST /images/delete unlink arbitrary *.mp4 files
- [SEC-002](security.md#sec-002-settings-close-link-renders-returnto-unchecked-javascript-xss): Settings "Close" link renders returnTo unchecked (javascript: XSS)
- [SEC-003](security.md#sec-003-ci-downloads-and-runs-unpinned-unverified-ffmpeg-builds): CI downloads and runs unpinned, unverified ffmpeg builds
- [ORG-001](organization.md#org-001-break-the-service-import-cycles-instead-of-hiding-them-in-local-imports): Break the service import cycles instead of hiding them in local imports
- [ORG-002](organization.md#org-002-share-the-changed-since-scan-guard-between-file-deletion-and-renaming): Share the "changed since scan" guard between file deletion and renaming
- [ORG-003](organization.md#org-003-encode-collection-membership-once): Encode collection membership once
- [ORG-004](organization.md#org-004-split-the-1025-line-viewer-page): Split the 1025-line viewer page
- [DOC-001](docs-consistency.md#doc-001-state-in-readme-security-that-the-open-api-can-delete-files-on-disk): State in README Security that the open API can delete files on disk
- [DOC-002](docs-consistency.md#doc-002-document-the-indexed-image-formats-heic-is-named-but-never-indexed): Document the indexed image formats; HEIC is named but never indexed
- [DOC-003](docs-consistency.md#doc-003-separate-the-unbuilt-image-analysis-plan-from-current-design-decisions): Separate the unbuilt "Image analysis" plan from current design decisions
- [TST-001](testing.md#tst-001-make-the-csrf-allowed-hosts-test-reach-the-allowed-hosts-rule): Make the CSRF allowed-hosts test reach the allowed-hosts rule
- [TST-002](testing.md#tst-002-test-the-viewer-pages-navigation-and-destructive-action-logic): Test the viewer page's navigation and destructive-action logic
- [TST-003](testing.md#tst-003-run-the-backend-tests-on-the-deployed-python-and-ffmpeg): Run the backend tests on the deployed Python and ffmpeg
- [TST-004](testing.md#tst-004-cover-rename-and-delete-failures-after-the-pre-checks-pass): Cover rename and delete failures after the pre-checks pass
- [PKG-002](packaging.md#pkg-002-declare-the-certifi-exclude-newer-exemption-that-uvlock-depends-on): Declare the certifi exclude-newer exemption that uv.lock depends on
- [PKG-003](packaging.md#pkg-003-run-ci-on-the-python-version-the-image-ships): Run CI on the Python version the image ships
- [GEN-002](general.md#gen-002-removing-a-source-while-it-is-scanned-brings-its-images-and-preset-back): Removing a source while it is scanned brings its images and preset back
- [GEN-003](general.md#gen-003-labelling-page-treats-imported-star-ratings-as-labels-and-deletes-them): Labelling page treats imported star ratings as labels and deletes them
- [GEN-004](general.md#gen-004-raising-the-perceptual-hash-version-re-reads-every-video): Raising the perceptual-hash version re-reads every video
- [GEN-005](general.md#gen-005-source-summary-lists-a-folder-once-per-duplicate-copy): Source summary lists a folder once per duplicate copy

### Low

- [SEC-004](security.md#sec-004-no-frame-ancestors--x-frame-options-clickjacking-bypasses-the-write-guard): No frame-ancestors / X-Frame-Options: clickjacking bypasses the write guard
- [SEC-005](security.md#sec-005-write-guards-fallback-trusts-any-loopback-port-and-every-wildcard-matched-host): Write guard's fallback trusts any loopback port and every wildcard-matched host
- [SEC-006](security.md#sec-006-dir-localsel-asks-to-permanently-trust-an-eval-that-loads-mutable-code): .dir-locals.el asks to permanently trust an eval that loads mutable code
- [SEC-007](security.md#sec-007-docker-base-images-are-pinned-by-mutable-tag-unlike-the-sha-pinned-actions): Docker base images are pinned by mutable tag, unlike the SHA-pinned actions
- [ORG-005](organization.md#org-005-use-one-sha-256-file-hasher): Use one SHA-256 file hasher
- [ORG-006](organization.md#org-006-derive-the-stored-video-format-in-one-place): Derive the stored video format in one place
- [ORG-007](organization.md#org-007-merge-the-two-ffprobe-wrappers): Merge the two ffprobe wrappers
- [ORG-008](organization.md#org-008-drop-vestigial-columns-sourcesenabled-and-imagesthumb_generated): Drop vestigial columns `sources.enabled` and `images.thumb_generated`
- [ORG-009](organization.md#org-009-remove-the-test-only-list_images-wrapper): Remove the test-only `list_images` wrapper
- [ORG-010](organization.md#org-010-remove-dead-code-in-apits-scanmanager-and-_page): Remove dead code in `api.ts`, `ScanManager` and `_page`
- [ORG-011](organization.md#org-011-use-copypath-and-one-failure-formatter-everywhere): Use `copyPath` and one failure formatter everywhere
- [ORG-012](organization.md#org-012-move-the-shared-grid-page-glue-into-gallery): Move the shared grid-page glue into `Gallery`
- [ORG-013](organization.md#org-013-share-the-settings-keyvalue-encoding): Share the `settings` key/value encoding
- [ORG-014](organization.md#org-014-name-the-duplicated-constants-once): Name the duplicated constants once
- [ORG-015](organization.md#org-015-trim-imagefileinfo-to-what-the-scan-uses): Trim `ImageFileInfo` to what the scan uses
- [ORG-016](organization.md#org-016-reuse-_record_sql-in-image_standings): Reuse `_record_sql` in `image_standings`
- [ORG-017](organization.md#org-017-raise-the-pydantic-settings-floor-and-drop-the-toml-import-fallback): Raise the pydantic-settings floor and drop the TOML import fallback
- [ORG-018](organization.md#org-018-drop-unused-parameters-and-single-use-indirection): Drop unused parameters and single-use indirection
- [DOC-004](docs-consistency.md#doc-004-bring-the-claudemd-code-layout-up-to-date): Bring the CLAUDE.md code layout up to date
- [DOC-005](docs-consistency.md#doc-005-document-the-label-page-linked-from-every-collection): Document the Label page linked from every collection
- [DOC-006](docs-consistency.md#doc-006-update-the-readme-feature-list): Update the README feature list
- [DOC-007](docs-consistency.md#doc-007-list-development-prerequisites-and-the-api-explorer-in-readme): List development prerequisites and the API explorer in README
- [DOC-008](docs-consistency.md#doc-008-correct-the-designmd-wording-on-all-images-and-source-presets): Correct the design.md wording on "All Images" and source presets
- [DOC-009](docs-consistency.md#doc-009-list-cachevideos-and-near-duplicatesjson-in-the-storage-descriptions): List cache/videos and near-duplicates.json in the storage descriptions
- [DOC-010](docs-consistency.md#doc-010-say-the-deploy-secrets-live-in-the-test-deploy-environment): Say the deploy secrets live in the test-deploy environment
- [DOC-011](docs-consistency.md#doc-011-fix-the-ciyml-comment-on-what-checksh-runs): Fix the ci.yml comment on what check.sh runs
- [DOC-012](docs-consistency.md#doc-012-fix-the-thalimage-devel-commentary-for-the-frontend-command): Fix the `thalimage-dev.el` commentary for the frontend command
- [TST-005](testing.md#tst-005-exercise-the-real-request-dependencies-at-least-once): Exercise the real request dependencies at least once
- [TST-006](testing.md#tst-006-measure-coverage-in-ci-and-for-the-frontend): Measure coverage in CI, and for the frontend
- [TST-007](testing.md#tst-007-close-the-sqlite-connections-the-tests-open): Close the SQLite connections the tests open
- [TST-008](testing.md#tst-008-type-check-the-test-suite): Type-check the test suite
- [PKG-004](packaging.md#pkg-004-pin-the-uv-version-for-developers-not-just-ci-and-docker): Pin the uv version for developers, not just CI and Docker
- [PKG-005](packaging.md#pkg-005-extend-dependabot-beyond-github-actions): Extend Dependabot beyond GitHub Actions
- [PKG-006](packaging.md#pkg-006-give-the-frontend-the-same-release-age-cooldown-as-the-backend): Give the frontend the same release-age cooldown as the backend
- [PKG-007](packaging.md#pkg-007-include-the-real-license-in-the-sdist-not-a-dangling-symlink): Include the real LICENSE in the sdist, not a dangling symlink
- [PKG-008](packaging.md#pkg-008-declare-starlette-which-the-backend-imports-directly): Declare starlette, which the backend imports directly
- [GEN-006](general.md#gen-006-thumbnails-and-previews-ignore-exif-orientation): Thumbnails and previews ignore EXIF orientation
- [GEN-007](general.md#gen-007-re-keying-in-a-scan-drops-pending-possible-edit-questions): Re-keying in a scan drops pending possible-edit questions
- [GEN-008](general.md#gen-008-derived-files-of-merged-or-purged-images-stay-in-the-cache-forever): Derived files of merged or purged images stay in the cache forever
- [GEN-009](general.md#gen-009-picture-hash-raises-indexerror-on-jpegs-cut-between-segments): Picture hash raises IndexError on JPEGs cut between segments
- [GEN-010](general.md#gen-010-label-page-says-no-images-while-loading-and-desyncs-after-a-failed-toggle): Label page says "no images" while loading, and desyncs after a failed toggle

## Cross-references

- PKG-001 and PKG-002 are one incident: the lock drift (PKG-002) is real at
  HEAD, and CI cannot see it because `make install` re-locks before the check
  (PKG-001).
- GEN-001 and GEN-004 interact: fix GEN-004 before raising
  `PERCEPTUAL_HASH_VERSION` for GEN-001, or every video is re-read again.
- ORG-004 / TST-002 (viewer page), PKG-003 / TST-003 (CI Python version),
  SEC-003 / TST-003 (CI ffmpeg), SEC-005 / TST-001 (write guard), SEC-007 /
  PKG-005 (base images), SEC-001 / DOC-001 (file deletion exposure),
  GEN-003 / DOC-005 (Label page).
- Merged during consolidation: the truncated-JPEG test gap is part of
  GEN-009; the `thalimage-dev.el` commentary mismatch is DOC-012.

## Skipped

- `docs/review/` (earlier runs).
- Historical docs, classified in [docs-consistency.md](docs-consistency.md)
  and not checked for drift: everything under `docs/archive/`.
- 18 backend tests that need ffmpeg were skipped locally (they pass in CI);
  no frontend coverage was measured (no coverage provider is installed, see
  TST-006).
- The Docker image was not built; statements about its contents are inferred
  from the Dockerfile.
