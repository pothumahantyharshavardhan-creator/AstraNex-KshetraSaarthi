"""Session-wide test fixtures.

The single job of this file is to point the backend at a throwaway SQLite
database *before* backend.db (or anything that imports it) is loaded, and to
initialise its schema — so `pytest` works from a clean checkout with no manual
setup step, and never touches a developer's real backend/astranex.db.

This module-level code runs the moment pytest collects this file, which is
before it imports any test module, which is before any test module can import
backend.main / backend.db. That ordering is what makes the isolation work.
"""
import os
import tempfile

_fd, _TEST_DB_PATH = tempfile.mkstemp(prefix="astranex-test-", suffix=".db")
os.close(_fd)
os.environ.setdefault("ASTRANEX_DB_PATH", _TEST_DB_PATH)
# Keep vision inference in fast, dependency-free context-only mode during tests
# unless a test explicitly wants otherwise.
os.environ.setdefault("ASTRANEX_AUTO_DOWNLOAD_MODEL", "0")

import atexit  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import init_db  # noqa: E402

# Create the schema up front. Endpoints that rely on FastAPI's lifespan startup
# event still work (init_db() is idempotent — every statement is CREATE TABLE
# IF NOT EXISTS), but tests no longer depend on that event actually firing,
# which is what made a bare `TestClient(app)` (no `with` block) fail with
# "no such table" errors on some Starlette/FastAPI versions.
init_db()


@atexit.register
def _cleanup_test_db():
    try:
        os.remove(_TEST_DB_PATH)
    except OSError:
        pass
