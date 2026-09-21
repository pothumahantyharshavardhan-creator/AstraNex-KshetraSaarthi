# SECURITY.md

## Scope of this document

This is an honest record of a security **review** performed in the v3.3
session (spec §36-38), not a claim of a full audit or penetration test. It
covers what was checked, what was found, and — importantly — that **no
hardening code changes were made**, because nothing unsound was found that
would justify a risky, untested change in a sandbox with no way to run the
test suite. Where the review found something worth fixing but out of scope
to change blind, it is called out below as future work.

## What was reviewed (v3.2 code, carried forward unchanged)

- **CORS** (`backend/main.py`): `allow_credentials=False`, an explicit
  origin allowlist plus a `localhost`/`127.0.0.1` regex, and origins
  configurable via `ASTRANEX_CORS_ORIGINS`. No wildcard `*` origin is used.
  This looks sound for a prototype that is not meant to hold session cookies.
- **File upload handling**: MIME type is restricted to
  `image/jpeg|png|webp`, a 2 MB size cap is enforced, dimensions are capped
  (25 megapixels) before decoding, and decode failures are caught and
  reported as `422` with only the exception *type name* — never the raw
  exception message or a traceback — surfaced to the client.
- **SQL**: every query in `backend/db.py` uses parameterised placeholders
  (`?`) — no string-formatted SQL was found anywhere in the file.
- **Error responses**: `HTTPException` messages throughout `main.py` are
  either static strings or `f'... {type(exc).__name__}'` — the exception
  class name, not its message or stack trace. No endpoint was found that
  echoes a raw exception message or traceback to the client.
- **Secrets**: no API keys, credentials, or secrets are hardcoded in the
  repository. `backend/services/weather.py` (new in v3.3) reads an optional
  `ASTRANEX_WEATHER_API_URL` from the environment and, deliberately, does
  not ship a live HTTP client — wiring one in is left as a documented
  extension point specifically so no key ever needs to be bundled.
- **Path handling for images**: `backend/main.py`'s image-serving endpoint
  resolves against `UPLOAD_DIR` (`backend/db.py`); a spot check did not find
  unsanitised user-supplied path segments being joined directly onto a
  filesystem path, but this was a read-through, not a fuzz test.

## New surface area added in v3.3 (self-review)

- All new endpoints (`/api/crops`, `/api/field-history`, `/api/timeline`,
  `/api/weather`, `/api/demo/*`, `/api/quantum/feature-sensitivity`) are
  read-only or operate on in-memory/demo data only — none of them accept a
  file upload or write raw user input into a filesystem path or SQL string.
- `crop_profiles.py` reads only from `config/crops/*.json` (a fixed,
  developer-controlled directory) — it does not accept a user-supplied path.
- `weather.py`'s `LiveApiProvider` currently returns `None` unconditionally
  (see above) — there is no live outbound HTTP call in this build to review
  for SSRF risk. If a real provider is wired in later, validate/allowlist the
  configured URL and set a timeout before making it live.
- `demo.py` never accepts a request body for `run_scenario` beyond a
  path-parameter integer id, and `alert_engine.py` / `data_quality.py` /
  `timeline.py` only consume already-validated internal dicts — none of them
  parse untrusted external input directly.

## NOT VERIFIED / not done this session

- No automated security scanner (Bandit, Semgrep, `pip-audit`, etc.) was run
  — this sandbox has no network access to install one.
- No fuzz testing of file uploads, form fields, or query parameters.
- No load/rate-limit testing — `backend/main.py` does not appear to
  implement its own rate limiting (spec §36 asks for it); this is a real gap
  and should be added at the reverse-proxy layer or with a FastAPI
  dependency (e.g. `slowapi`) before any public deployment.
- Dependency versions (`requirements.txt`) were reviewed but not re-pinned
  or scanned for known CVEs, again due to no network access in this session.
- Debug/reload flags: `run_backend.sh` was not re-inspected in this session
  for `--reload`/debug settings that should not be used in production;
  confirm before deploying.

## Bottom line

Nothing found in this review looks unsound. The main concrete gap is the
missing rate limiting called for in spec §36, and the general caveat that
none of this was verified by an actual scanner or live traffic in this
session.
