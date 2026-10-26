# Testing review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

8 findings: 4 medium, 4 low.

**How tests run.** Backend: pytest with xdist, pytest-asyncio and pytest-cov,
in `backend/tests/` (62 files, ~9.1k lines; fixtures in `conftest.py`,
seeding in `helpers.py`). Frontend: vitest on jsdom, 29 `*.test.ts` files
next to the modules in `frontend/src/lib/`. `./check.sh` runs `make test`
(`pytest -q -n auto`) then `make fe-check fe-test`; CI installs ffmpeg and
runs `./check.sh`. Coverage exists only as `make cov`, which CI does not run;
the frontend has no coverage script or provider.

**Results.** `./check.sh` passed (with the temporary certifi exemption, see
PKG-002): 647 backend passed, 18 skipped; svelte-check 0 errors; 205 frontend
tests passed. `make cov`: 647 passed, 18 skipped, 14 `ResourceWarning:
unclosed database`; **backend coverage 92%** (3414 statements, 225 missed;
802 branches, 77 partial). Lowest locally: `services/playable_copies.py` 19%,
`core/video.py` 53%, `deps.py` 74%, `core/picture_hash.py` 86%,
`__main__.py` 0%.

**The 18 skips** are all `requires_ffmpeg` (`backend/tests/helpers.py:15`):
12 in `test_playable_copies.py`, 4 in `test_video.py`, 2 in
`test_scan_service.py`; this VM has no ffmpeg. CI runs them: the latest main
run (job 121647894854) shows 665 passed, 0 skipped. So the low video coverage
is local only, but locally `check.sh` stays green without saying the video
tests were skipped.

**Quality.** Every backend test has an `assert` or `pytest.raises` (AST scan),
every frontend test an `expect`; no `skip`/`only`/`todo` beyond the ffmpeg
marker and two backend-only-checkout guards. Mocking is light (real scans via
`TestClient` and real files). Destructive operations are well covered on main
and refusal paths, and every data-changing migration (003, 009, 010, 011, 013,
014, 018, 020, 022, 025) has a data-preserving test.

The truncated-JPEG test gap found here is reported with the bug it hides, as
GEN-009.

## TST-001: Make the CSRF allowed-hosts test reach the allowed-hosts rule

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/tests/test_csrf.py:63-75`, `backend/src/thalimage/csrf.py:21-28`, `backend/src/thalimage/csrf.py:58-61`
- **Labels:** testing, area:backend, security

`test_origins_of_allowed_hosts_pass` sends `host: box.tail1234.ts.net` with
`origin: https://box.tail1234.ts.net`; the origin's netloc equals Host, so
`_allowed` returns at the same-origin check (`csrf.py:58`) and never calls
`_host_matches` (`csrf.py:61`). Coverage confirms `csrf.py` lines 25 and 27
(both `return True` branches of `_host_matches`) never run: the exact-host
and `*.domain` matches of the write guard are untested, despite the docstring.

**Why it matters:** this middleware is the only write protection in an app
without authentication; a regression would pass CI.

**Suggested fix:** cases where Origin differs from Host but matches
`allowed_hosts` (exact, `*.ts.net`, `*`), and negatives (`evilts.net` against
`*.ts.net`, an origin with a port).

**Done when:** `make cov` reports `csrf.py` at 100% lines and branches, and the
new tests fail if `_host_matches` returns `False`.

See also: SEC-005 (the rule itself is too broad).

## TST-002: Test the viewer page's navigation and destructive-action logic

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/routes/image/[hash]/+page.svelte:70-74`, `frontend/src/routes/image/[hash]/+page.svelte:113-207`, `frontend/src/routes/image/[hash]/+page.svelte:269-430`, `frontend/src/routes/image/[hash]/+page.svelte:456-509`, `frontend/vite.config.ts:41`
- **Labels:** testing, area:frontend

vitest collects only `src/**/*.test.ts`, and no `.svelte` component or route
has a test. The 1025-line viewer page carries real logic: the neighbour window
(`windowCovers`, `refreshWindow`, the `windowInFlight`/`loadSeq` race guards),
`navigate`, a 160-line `onKeydown`, and delete/rename confirmations whose hash
is pinned "so navigating cannot change what gets deleted" (line 70).
Comparable logic elsewhere lives in tested modules (`gallery.svelte.ts`,
`gridPaging.ts`, `eloRound.svelte.ts`).

**Why it matters:** a regression in which image a delete or rename targets
acts on the user's files; paging races show the wrong image; CI catches
neither.

**Suggested fix:** move window, paging and confirmation state into a
`lib/viewer.svelte.ts`-style module and unit-test it (alternatives:
`@testing-library/svelte` page tests, or an end-to-end test).

**Done when:** tests cover the refetch at `WINDOW_EDGE` and the listing ends,
a stale load not overwriting a newer one, delete/rename acting on the pinned
hash after navigating, and the key bindings.

See also: ORG-004 (the same page from the structure side).

## TST-003: Run the backend tests on the deployed Python and ffmpeg

- **Severity:** medium
- **Confidence:** high
- **Location:** `.github/workflows/ci.yml:15-18`, `.github/workflows/ci.yml:33-53`, `docker/Dockerfile:19-25`, `backend/pyproject.toml:9`
- **Labels:** testing, area:ci

Production runs `python:3.11-slim` with Debian's `ffmpeg`
(`Dockerfile:19,24`). CI pins no interpreter, so uv uses the runner's
`CPython 3.12.3`, and it downloads BtbN's `ffmpeg-master-latest`, which on the
inspected run was a same-day nightly (`N-128100-…-20261026`). The suite has
never run on 3.11, and the video tests run against a moving ffmpeg master
rather than what ships. The SQLite library also differs (Ubuntu system Python
vs the Debian image); versions not compared.

**Why it matters:** interpreter, SQLite or ffmpeg differences can pass CI and
fail in production, or CI can break on an unrelated ffmpeg nightly.

**Suggested fix:** pin Python 3.11 in CI (see PKG-003), and either run the
backend tests inside the built image or install a pinned ffmpeg matching
Debian's major version.

**Done when:** the CI log shows CPython 3.11.x and a fixed ffmpeg version, and
two runs on different days use the same ffmpeg.

See also: PKG-003 (Python version), SEC-003 (unverified ffmpeg download).

## TST-004: Cover rename and delete failures after the pre-checks pass

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/services/file_renaming.py:110-111`, `backend/src/thalimage/services/file_renaming.py:144-151`, `backend/src/thalimage/services/file_renaming.py:202-204`, `backend/src/thalimage/services/file_deletion.py:154-155`
- **Labels:** testing, area:files

Coverage shows these never run: a rename whose `os.rename` (or `remove_copy`)
fails (`file_renaming.py:150-151`); a hash name appearing between `_refusal`
and `_rename` (145-148); a failing sidecar rename (203-204); the "file
vanished since the scan" branch of both the rename and delete refusals
(`file_renaming.py:110-111`, `file_deletion.py:154-155`). Existing failure
tests reach only the pre-checks (`test_rename_at_scan.py:98` is refused by
`_refusal`; the chmod test at `:115` stops at the folder check).

**Why it matters:** these branches decide whether the database still matches
the user's files after a partial failure on operations that modify their disk.

**Suggested fix:** monkeypatch `os.rename` (or the `change_file` callback) to
raise for one file; delete the media file between scan and request; assert
the failure entry, the unchanged `image_locations` row, and unmoved sidecars.

**Done when:** `make cov` shows those lines covered, with assertions on disk
and database state.

## TST-005: Exercise the real request dependencies at least once

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/tests/conftest.py:65-70`, `backend/src/thalimage/deps.py:53-85`
- **Labels:** testing, area:backend

The `client` fixture overrides `get_thumb_dir`, `get_preview_dir`,
`get_video_dir`, `get_scan_manager` and `get_backup_scheduler`; no request
runs the real getters (`deps.py` 74%, lines 55-85 missed). They read untyped
`request.app.state.*` attributes set in `app.py:62-65`, which mypy cannot
check.

**Why it matters:** renaming a state attribute or settings property would
break every thumbnail, preview, video, scan and backup endpoint while the
suite stays green.

**Suggested fix:** one smoke test starting `create_app()` with its lifespan on
a temp data dir (as `test_app.py:139` does) and no overrides, hitting a thumb,
preview, scan-status and backups endpoint.

**Done when:** `deps.py` is covered and the test fails if one of those
`app.state` names changes.

## TST-006: Measure coverage in CI, and for the frontend

- **Severity:** low
- **Confidence:** high
- **Location:** `check.sh:18`, `Makefile:9-13`, `frontend/package.json:9-17`
- **Labels:** testing, area:ci

`check.sh` runs `make test`, not `make cov`, so CI never measures coverage or
enforces a floor; the frontend has no coverage script and no
`@vitest/coverage-v8`. Video modules are covered only where ffmpeg exists, so
local numbers mislead without the CI figure.

**Why it matters:** coverage can drop silently; the gap in TST-002 (no
component or route tested) is visible nowhere.

**Suggested fix:** run coverage in CI with `--cov-fail-under` at the current
level; add `vitest run --coverage` with the v8 provider and a threshold.

**Done when:** the CI log prints backend and frontend coverage, and the job
fails below the agreed thresholds.

## TST-007: Close the SQLite connections the tests open

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/tests/test_identity_upgrade.py:24-40`, `backend/tests/test_identity_upgrade.py:112-114`, `backend/tests/test_migrations.py:32-35`
- **Labels:** testing, area:backend

`make cov` emits 14 `ResourceWarning: unclosed database`, attributed to
whichever test triggers GC and hidden under `-n auto`. Two sources are
confirmed: the `Library` fixture opens `self.conn` and never closes it (7
tests), and `test_migrate_stops_at_target` never closes its connection. Other
leaks, including in production code, are not ruled out; a full run with
`PYTHONTRACEMALLOC` would show where each was opened.

**Why it matters:** test noise hides real production leaks, and on Windows
open connections hold `tmp_path` files.

**Suggested fix:** make `Library` a yield fixture that closes its connection,
close it in `test_migrate_stops_at_target`, then add
`filterwarnings = ["error::ResourceWarning"]` to `[tool.pytest.ini_options]`.

**Done when:** `make cov` reports no `ResourceWarning`, and an unclosed
`connect()` in a test fails the suite.

## TST-008: Type-check the test suite

- **Severity:** low
- **Confidence:** high
- **Location:** `Makefile:21-22`
- **Labels:** testing, area:backend

`make typecheck` runs `mypy src/` only. The tests are fully annotated
(fixtures, `TestClient`, `sqlite3.Connection`, `pytest.MonkeyPatch`), but
nothing checks them, so a fixture of the wrong type or a helper called with
stale arguments after a signature change shows up only at runtime, or never.

**Why it matters:** type checks keep tests in step with the code they test.

**Suggested fix:** `mypy src/ tests/`, fixing or ignoring per module.

**Done when:** `make typecheck` covers `backend/tests/` and passes.
