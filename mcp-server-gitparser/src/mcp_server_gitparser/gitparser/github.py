"""
Async parser for converting GitHub repositories to Markdown using gitingest.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

from gitingest import ingest_async

logger = logging.getLogger(__name__)


def is_valid_github_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in {"github.com", "www.github.com"} and bool(parsed.path)


def clean_github_url(url: str) -> str:
    parsed = urlparse(url)
    clean_path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{clean_path}"


async def convert_repo_to_markdown(
    repo_url: str,
    token: Optional[str] = None,
    include_submodules: bool = False,
    include_gitignored: bool = False,
) -> str:
    repo_url = clean_github_url(repo_url)
    if not is_valid_github_url(repo_url):
        raise ValueError(f"Invalid GitHub URL: {repo_url}")

    try:
        logger.info("Converting GitHub repository: %s", repo_url)
        summary, tree, content = await ingest_async(
            repo_url,
            token=token,
            include_submodules=include_submodules,
            include_gitignored=include_gitignored,
        )
        markdown_output = f"""# Repository Digest: {repo_url}

## Summary

{summary}

## Directory Structure

{tree}

## Content

{content}
"""
        logger.info("Successfully converted repository: %s", repo_url)
        return markdown_output
    except Exception as e:  # noqa: BLE001
        logger.error("Error converting repository %s: %s", repo_url, e)
        raise RuntimeError(f"Failed to convert repository: {str(e)}") from e

