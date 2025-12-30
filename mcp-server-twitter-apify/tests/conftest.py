from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add src to sys.path so that mcp_twitter and db can be imported
# This is necessary because the tests are outside the src directory
# and the package might not be installed in editable mode in the current environment.
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


class FixedDatetime:
    """Simple datetime stub for deterministic filenames in tests."""

    @classmethod
    def now(cls) -> "FixedDatetime":  # noqa: D102
        return cls()

    def strftime(self, fmt: str) -> str:  # noqa: D102
        # The code under test uses "%Y%m%d_%H%M%S"
        return "20250101_010203"


@pytest.fixture
def fixed_datetime() -> type[FixedDatetime]:
    return FixedDatetime


@pytest.fixture
def tmp_results_dir(tmp_path: Path) -> Path:
    d = tmp_path / "results"
    d.mkdir()
    return d


