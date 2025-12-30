from __future__ import annotations

import re

import mcp_twitter.twitter.models as models
from mcp_twitter.twitter import QueryDefinition, TwitterScraperInput


def test_output_filename_uses_explicit_output_and_adds_json_extension() -> None:
    q = QueryDefinition(
        id="x",
        type="topic",
        name="n",
        input=TwitterScraperInput(searchTerms=["hello"]),
        output="my_file",
    )
    assert q.output_filename() == "my_file.json"


def test_output_filename_autogenerates_safe_filename_with_timestamp(monkeypatch) -> None:
    class FakeDatetime:
        @classmethod
        def now(cls):  # noqa: ANN001
            return cls()

        def strftime(self, fmt: str) -> str:  # noqa: ARG002
            return "20250101_010203"

    monkeypatch.setattr(models, "datetime", FakeDatetime)
    q = QueryDefinition(
        id="x",
        type="topic",
        name="n",
        input=TwitterScraperInput(searchTerms=["hello world:again"]),
        output=None,
    )
    out = q.output_filename()
    assert out == "twitter_results_hello_world_again_20250101_010203.json"
    assert re.match(r"^twitter_results_.*\.json$", out)


