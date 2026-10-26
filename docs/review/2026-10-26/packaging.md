# Packaging review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

8 findings: 1 high, 2 medium, 5 low. Reviewed the committed state
(`git show HEAD:backend/pyproject.toml`; the review ran with a temporary,
uncommitted certifi exemption in the working tree so the gate could run).

The headline pair: `uv.lock` holds the #171 certifi upgrade through an
exemption `pyproject.toml` does not declare (PKG-002), and CI cannot see it
because `make install` re-locks on the runner before `check.sh` checks the
lock (PKG-001). The CI job log for 4f48e65 (job 121647894854) shows uv
0.12.22 re-resolving ("Resolving despite existing lockfile due to removal of
exclude newer for package `certifi`"), installing `certifi==2026.10.18`, and
then `uv lock --check` passing against the rewritten lock. The CI uv version
is not the cause: both 0.12.22 and the local 0.13.5 resolve the same way.

Commands run (read-only towards the repo): `uv lock --check` and
`uv lock --dry-run` on a `git archive HEAD` copy, `uv build` on the same copy,
`gh api` for the CI job log.

## PKG-001: Stop CI's `make install` rewriting uv.lock before the lock check

- **Severity:** high
- **Confidence:** high
- **Location:** `.github/workflows/ci.yml:56-60`, `Makefile:5-6`, `Makefile:25-26`, `check.sh:8-9`
- **Labels:** packaging, area:ci

CI runs `make install` (`cd backend && uv sync`, neither `--locked` nor
`--frozen`) and only then `./check.sh`, whose first step is `uv lock --check`.
A plain `uv sync` re-resolves and rewrites `uv.lock` when it disagrees with
`pyproject.toml`. The 4f48e65 job log shows exactly that: "Resolving despite
existing lockfile due to removal of exclude newer for package `certifi`",
`+ certifi==2026.10.18`, then `=== Lock ===` passing. The other `uv run`
targets (`Makefile:9-34`) re-lock the same way locally.

**Why it matters:** the lock check can never fail in CI, and it hid PKG-002;
CI tests a different dependency set from the committed lock and the image.

**Suggested fix:** `uv sync --locked` in `make install`, or `UV_LOCKED=1` in
the CI job env; or run the lock check before any sync.

**Done when:** a CI run on a commit whose `uv.lock` disagrees with
`pyproject.toml` fails, and `git diff --exit-code backend/uv.lock` after
`make install` passes in CI.

## PKG-002: Declare the certifi exclude-newer exemption that uv.lock depends on

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/pyproject.toml:61-63`, `backend/uv.lock:5-10`, `backend/uv.lock:44-47`
- **Labels:** packaging, area:backend

PR #171 (e11b62d) changed only `backend/uv.lock`, which now records
`[options.exclude-newer-package] certifi = false` and pins certifi
2026.10.19; `[tool.uv]` still declares only `exclude-newer = "7 days"`. On the
committed tree `uv lock --check` fails and `uv lock --dry-run` reports
`Update certifi v2026.10.19 -> v2026.10.18`. certifi is reached only through
the dev dependencies `httpx`/`httpcore`, and the image uses `uv sync --frozen`,
so the runtime is not exposed.

**Why it matters:** the fix exists only in the lock: any routine `uv sync`,
`uv run` or `uv lock` reinstates the compromised roots (GHSA-6q48-6c7w-9gw2)
in dev environments and a later lock commit undoes #171; the gate fails at
HEAD for every developer.

**Suggested fix:** add `exclude-newer-package = { certifi = false }` under
`[tool.uv]` (or a `certifi>=2026.10.19` floor); drop the exemption once
2026.10.19 is past the 7-day window. Consider `uv sync --locked` in
`docker/Dockerfile:39,45`.

**Done when:** `cd backend && uv lock --check` passes on a clean checkout
with the CI and local uv versions, and `uv lock --dry-run` reports no certifi
change.

**Details:** [details/PKG-002.md](details/PKG-002.md)

## PKG-003: Run CI on the Python version the image ships

- **Severity:** medium
- **Confidence:** high
- **Location:** `.github/workflows/ci.yml:15-18`, `docker/Dockerfile:19`, `backend/pyproject.toml:9`, `backend/pyproject.toml:52`
- **Labels:** packaging, area:ci

The image runs `python:3.11-slim` and mypy targets 3.11, but CI passes no
Python version to setup-uv and the repo has no `.python-version`, so uv uses
the runner's interpreter: the CI log shows "Using CPython 3.12.3 interpreter
at: /usr/bin/python3" (locally uv picked 3.13.5). The backend tests have never
run on 3.11, the production interpreter and declared minimum.

**Why it matters:** code relying on 3.12+ behaviour passes CI and breaks only
in the container.

**Suggested fix:** commit `backend/.python-version` with `3.11`, or pass
`python-version: "3.11"` to setup-uv; optionally a matrix entry for the newest.

**Done when:** the CI log's "Using CPython" line reports 3.11.x.

See also: TST-003 (the same gap seen from the test side, plus ffmpeg).

## PKG-004: Pin the uv version for developers, not just CI and Docker

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/pyproject.toml:61-63`, `.github/workflows/ci.yml:17`, `docker/Dockerfile:28`
- **Labels:** packaging, area:tooling

CI and the image pin uv 0.12.22 as two separate literals; `[tool.uv]` has no
`required-version` and the README names none (this VM has 0.13.5). Lock
options such as `exclude-newer-span`/`exclude-newer-package` are
version-sensitive, so versions can disagree about whether the lock is current.
Here both agree (PKG-002), so the risk is latent.

**Why it matters:** the lock check can give different verdicts on different
machines, and the CI and Docker pins can drift apart.

**Suggested fix:** `required-version` under `[tool.uv]`; optionally have
setup-uv read the version from `pyproject.toml` so there is one source.

**Done when:** a uv outside the declared range refuses to run in `backend/`,
and the CI and Dockerfile pins match it.

## PKG-005: Extend Dependabot beyond GitHub Actions

- **Severity:** low
- **Confidence:** medium
- **Location:** `.github/dependabot.yml:4-14`
- **Labels:** packaging, area:ci, security

`dependabot.yml` lists only `github-actions`: no `uv` (`backend/`), `npm`
(`frontend/`) or `docker` (the `node:24-slim`, `python:3.11-slim` and
`ghcr.io/astral-sh/uv:0.12.22` bases). The certifi fix in #171 was manual.
Whether GitHub security updates are enabled in the repo settings is not
visible from the repo.

**Why it matters:** Python, JS and base-image dependencies get no update PRs;
fixes like certifi's depend on someone noticing.

**Suggested fix:** add `uv`, `npm` and `docker` entries with the same
schedule and 7-day cooldown.

**Done when:** Dependabot opens update PRs for `backend/uv.lock`,
`frontend/pnpm-lock.yaml` and the Dockerfile bases.

See also: SEC-007 (base images pinned by mutable tag).

## PKG-006: Give the frontend the same release-age cooldown as the backend

- **Severity:** low
- **Confidence:** medium
- **Location:** `frontend/pnpm-workspace.yaml:1-7`, `backend/pyproject.toml:61-63`, `.github/dependabot.yml:11-14`
- **Labels:** packaging, area:frontend, security

The backend resolves only releases at least 7 days old and Dependabot waits 7
days for actions ("a compromised release time to be caught"), but
`pnpm-workspace.yaml` sets no `minimumReleaseAge`, so `pnpm update`/`add` can
pull a minutes-old release. (pnpm supports the setting from 10.16 to the
reviewer's knowledge; 10.28.0 is pinned. Not verified.)

**Why it matters:** npm is the ecosystem most often hit by compromised
releases and the one left without the delay.

**Suggested fix:** `minimumReleaseAge: 10080` (minutes) in
`frontend/pnpm-workspace.yaml`.

**Done when:** `pnpm add` of a version under 7 days old is refused in
`frontend/`.

## PKG-007: Include the real LICENSE in the sdist, not a dangling symlink

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/LICENSE` (symlink to `../LICENSE`), `backend/pyproject.toml:13-16`
- **Labels:** packaging, area:backend

`uv build` on a HEAD copy puts `thalimage-0.8.0/LICENSE -> ../LICENSE` in the
sdist, dangling once extracted; the wheel built from that sdist (the default
`uv build` path) has no `dist-info/licenses/LICENSE` although METADATA says
`License-File: LICENSE`. A wheel built from the tree includes it, and the
Dockerfile works around it with `COPY LICENSE` (`docker/Dockerfile:42-44`).

**Why it matters:** the proprietary licence terms go missing from built
artifacts while the metadata names the file.

**Suggested fix:** commit a real `backend/LICENSE` identical to the root one
(a check can enforce it), or otherwise make hatchling archive the contents.

**Done when:** `uv build` yields a wheel containing
`thalimage-0.8.0.dist-info/licenses/LICENSE`, and the sdist's LICENSE is a
regular file.

## PKG-008: Declare starlette, which the backend imports directly

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/compression.py:11-13`, `backend/src/thalimage/csrf.py:14-16`, `backend/src/thalimage/app.py:13`, `backend/pyproject.toml:18-28`
- **Labels:** packaging, area:backend

Three modules import `starlette` directly, including middleware internals
(`GZipResponder`, `IdentityResponder`, `compression.py:12`), but `starlette`
is not in `[project].dependencies`; it arrives only via fastapi (1.0.0).

**Why it matters:** a fastapi upgrade can move the starlette range and break
the subclassed internals silently.

**Suggested fix:** add `starlette` with a range covering the tested version
(e.g. `starlette>=1.0,<2`).

**Done when:** `starlette` is in `[project].dependencies` and
`uv lock --check` passes.
