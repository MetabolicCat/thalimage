# Security review: thalimage

Scope: repository root · Commit: 4f48e65 · Date: 2026-10-26

7 findings: 3 medium, 4 low. Authn/authz was judged with the tailnet as the
boundary (in-app auth is #128): the findings break the app's own stated
guarantees (the writable-source gate and the cross-site write guard) rather
than restating that there is no login.

Covered: middleware (`csrf.py`, TrustedHost, CORS, SPA fallback), every API
router, file-touching services (delete, rename, merge, sidecars, backups,
previews, ffmpeg subprocesses), SQL construction, metadata parsing, the
frontend's URL and query-param sinks, `{@html}`, the service worker, the
Dockerfile, entrypoint, compose, `serve.json`, `.env.example`, CI and publish
workflows, manifests and lockfiles, dev tooling, a search for secrets and for
text addressed to AI agents.

Checked and clean: SQL uses bound parameters throughout and sort/direction/
filter names are matched against fixed lists; path params are constrained by
the `ContentHash` and `DocSlug` regexes; the SPA fallback checks
`is_relative_to`; XMP goes through defusedxml; no pickle, yaml, eval or
`shell=True`, and ffmpeg/ffprobe get argument lists; temp files use `mkstemp`
or `TemporaryDirectory`; no committed secrets; no text addressed to AI agents;
actions are SHA-pinned and the publish job is gated off fork and Dependabot
PRs.

The certifi lock mismatch (PKG-002) has little security impact: certifi comes
in only through the dev dependencies `httpx`/`httpcore`, the backend makes no
outbound TLS connections, and the image installs with `uv sync --frozen`.

## SEC-001: Unvalidated hashes in POST /images/delete unlink arbitrary *.mp4 files

- **Severity:** medium
- **Confidence:** high
- **Location:** `backend/src/thalimage/api/images.py:306-307`, `backend/src/thalimage/api/images.py:445-460`, `backend/src/thalimage/core/video.py:179-181`, `backend/src/thalimage/services/file_deletion.py:331-340`
- **Labels:** security, area:backend

`ImagesBody.hashes` is a bare `list[str]` (images.py:307), unlike the path
params held to the `ContentHash` pattern. `delete_several_images_files`
passes each value to `playable_copy_path(video_dir, h).unlink(missing_ok=True)`
whenever `is_live` is false (images.py:457-459), and an unknown value is
always "not live" (`delete_images` skips it, file_deletion.py:340).
`playable_copy_path` builds `video_dir / h[:2] / f"{h}.mp4"`: with
`h = "/images/clip"` pathlib's absolute-operand rule gives `/images/clip.mp4`;
`h = "../../x"` walks out of `video_dir`.

**Why it matters:** one POST deletes any `.mp4` the app user can write,
anywhere, bypassing the writable-source gate, the last-copy guard and the
`file_changes` record.

**Suggested fix:** constrain `ImagesBody.hashes` items to `^[0-9a-f]{64}$`
(annotated `str` with `pattern=`); optionally assert a hex key in
`playable_copy_path`/`thumbnail_path`/`preview_path`.

**Done when:** `POST /api/v1/images/delete` with `{"hashes": ["/tmp/x"]}` or
`["../x"]` returns 422, and a test shows an `.mp4` outside `video_dir`
survives the request.

## SEC-002: Settings "Close" link renders returnTo unchecked (javascript: XSS)

- **Severity:** medium
- **Confidence:** high
- **Location:** `frontend/src/routes/settings/+page.svelte:30`, `frontend/src/routes/settings/+page.svelte:141`
- **Labels:** security, area:frontend

`backHref` is `$page.url.searchParams.get('returnTo') || '/'` and goes
straight into `<a href={backHref}>Close</a>`. Svelte does not sanitise URL
attributes, and SvelteKit leaves a `javascript:` URL to the browser, so
`/settings?returnTo=javascript:fetch('/api/v1/sources/1',{method:'DELETE'})`
runs in the app's origin when the victim clicks Close. The same parameter is
an open redirect (`returnTo=https://evil.example`).

**Why it matters:** same-origin script passes the cross-site write guard by
design, so a link sent to a tailnet user can delete sources, images in
writable sources, or collections. Tailscale HTTPS names are in CT logs.

**Suggested fix:** accept `returnTo` only if it starts with `/`, not `//` or
`/\`, and resolves to `location.origin`; otherwise `/`. Put the check next to
`settingsHref` in `lib/settingsLink.ts` and unit-test it.

**Done when:** `returnTo=javascript:alert(1)`, `//evil.example` and
`https://evil.example` each render `href="/"`, and `/collections/3?sort=name`
still round-trips.

## SEC-003: CI downloads and runs unpinned, unverified ffmpeg builds

- **Severity:** medium
- **Confidence:** high
- **Location:** `.github/workflows/ci.yml:33-54`, `.github/workflows/ci.yml:1-10`
- **Labels:** security, area:ci

"Install ffmpeg" pipes `curl` into `tar` for
`.../releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz` (a
moving nightly), falling back to `johnvansickle.com`, then executes the
binaries with no checksum or signature check; pytest runs them again.
`ci.yml` declares no `permissions:`, so the job gets the default
`GITHUB_TOKEN` scope, which `actions/checkout` persists in `.git/config`; the
uv and pnpm caches are saved after the run.

**Why it matters:** a tampered upstream build runs in every CI job, can read
the token and poison the caches later runs restore; it is the weakest link in
otherwise SHA-pinned workflows.

**Suggested fix:** add `permissions: contents: read`; install ffmpeg from apt
or one fixed release URL checked against a committed SHA-256; set
`persist-credentials: false` on checkout.

**Done when:** `ci.yml` has an explicit read-only `permissions:` block, and
the ffmpeg source is apt or a fixed URL whose digest is checked before use.

See also: TST-003 (CI tests against a moving ffmpeg nightly).

## SEC-004: No frame-ancestors / X-Frame-Options: clickjacking bypasses the write guard

- **Severity:** low
- **Confidence:** high
- **Location:** `backend/src/thalimage/app.py:95-118`, `backend/src/thalimage/csrf.py:1-9`, `docker/serve.json:1-16`
- **Labels:** security, area:backend

No response carries `Content-Security-Policy: frame-ancestors`,
`X-Frame-Options` or `X-Content-Type-Options` (repository-wide search), and
`tailscale serve` adds none. A page on another site, open in a tailnet
browser, can frame the app and trick clicks onto Delete, Merge or confirm
dialogs; requests from the frame are same-origin, so `CrossSiteWriteGuard`
passes them, which is the threat the README's Security section says the app
guards against.

**Why it matters:** sidesteps the only in-app control against hostile pages.

**Suggested fix:** a small middleware setting `Content-Security-Policy:
frame-ancestors 'none'`, `X-Frame-Options: DENY` and
`X-Content-Type-Options: nosniff` on the SPA shell and API responses.

**Done when:** a test asserts `/` and `/api/v1/version` carry
`frame-ancestors 'none'` and `X-Frame-Options: DENY`.

## SEC-005: Write guard's fallback trusts any loopback port and every wildcard-matched host

- **Severity:** low
- **Confidence:** medium
- **Location:** `backend/src/thalimage/csrf.py:20-28`, `backend/src/thalimage/csrf.py:46-60`, `backend/src/thalimage/app.py:100`, `docker/docker-compose.yml:101`
- **Labels:** security, area:backend

When `Sec-Fetch-Site` is not `cross-site`, `_allowed` accepts any Origin whose
hostname matches `allowed_hosts`, ignoring the port (csrf.py:60), and
`localhost`/`127.0.0.1` are always allowed (app.py:100). On a desktop install,
a page served by another local server on `127.0.0.1:<port>` is same-site and
passes. The compose default `["*.ts.net"]` matches every tailnet; browsers
without `Sec-Fetch-Site` (Safari < 16.4) are then guarded only by that
wildcard. Whether `ts.net` is on the Public Suffix List was not checked.

**Why it matters:** the guard is meant to refuse other sites; hostname-only
matching lets other origins on the same host or wildcard write.

**Suggested fix:** in the fallback, require Origin's scheme and netloc to
equal the request's own (or an explicit `cors_origins` entry); recommend the
exact MagicDNS name instead of `*.ts.net` in compose and `.env.example`.

**Done when:** a POST with `Origin: http://127.0.0.1:3000` to Host
`127.0.0.1:8000` gets 403, and so does `Origin: https://other.tailxyz.ts.net`
without `Sec-Fetch-Site` against Host `thalimage.tail123.ts.net`.

See also: TST-001 (the allowed-hosts rule has no test reaching it).

## SEC-006: .dir-locals.el asks to permanently trust an eval that loads mutable code

- **Severity:** low
- **Confidence:** medium
- **Location:** `.dir-locals.el:5-14`, `thalimage-dev.el:20-21`
- **Labels:** security, area:tooling

`.dir-locals.el` runs an `eval` that `load`s whichever `thalimage-dev.el`
`locate-dominating-file` finds, and its comment tells the user to answer "!"
to mark it permanently safe. Emacs whitelists the form, not the loaded file's
contents, so any branch or PR checked out for review that changes
`thalimage-dev.el` then runs its Elisp without a prompt.

**Why it matters:** reviewing an untrusted or agent-authored branch locally
becomes code execution on the reviewer's machine.

**Suggested fix:** drop the "answer !" advice and the auto-load; load
`thalimage-dev.el` explicitly from the user's init.

**Done when:** visiting a file in a fresh checkout loads no project Elisp
without a prompt, and nothing recommends marking the eval permanently safe.

## SEC-007: Docker base images are pinned by mutable tag, unlike the SHA-pinned actions

- **Severity:** low
- **Confidence:** high
- **Location:** `docker/Dockerfile:2`, `docker/Dockerfile:19`, `docker/Dockerfile:28`
- **Labels:** security, area:deployment

`node:24-slim`, `python:3.11-slim` and `ghcr.io/astral-sh/uv:0.12.22` are
referenced by tag, which the publisher can move, so released images are built
from whatever the tags point to at build time (and the shared registry build
cache makes that harder to see).

**Why it matters:** a re-pointed or compromised upstream tag goes straight
into `ghcr.io/rki027/thalimage:latest`; actions get SHA pins and a cooldown,
base images neither.

**Suggested fix:** pin each `FROM`/`COPY --from` to `tag@sha256:<digest>`.

**Done when:** every image reference in `docker/Dockerfile` carries an
`@sha256:` digest.

See also: PKG-005 (Dependabot does not watch `/docker`, so nothing would bump the digests).
