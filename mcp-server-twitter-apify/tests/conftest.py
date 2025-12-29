from __future__ import annotations

from pathlib import Path

import pytest


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


