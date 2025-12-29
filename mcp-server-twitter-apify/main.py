from __future__ import annotations

"""
Backward-compatible entrypoint.

Supports:
  - `python -m main ...`
  - `python main.py ...`

Implementation lives in `src/mcp_twitter/`.
"""

import sys
from pathlib import Path

from mcp_twitter.logger import get_logger

# Ensure `src/` is importable when running from a source checkout (without installing).
_src = (Path(__file__).resolve().parent / "src").as_posix()
if _src not in sys.path:
    sys.path.insert(0, _src)

log = get_logger(__name__)


def _check_db_connection() -> None:
    """Verify database connectivity on startup."""
    try:
        from db import get_db_instance  # Imported here after sys.path adjustment

        get_db_instance()
        log.info("Database connection check: OK")
    except Exception as exc:  # pragma: no cover - defensive startup check
        log.error("Database connection check failed: %s", exc)
        raise


from mcp_twitter.cli import main

if __name__ == "__main__":
    _check_db_connection()
    raise SystemExit(main())


