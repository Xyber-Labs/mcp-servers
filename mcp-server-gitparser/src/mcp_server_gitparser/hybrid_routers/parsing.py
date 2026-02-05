from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter

from mcp_server_gitparser.config import get_app_settings
from mcp_server_gitparser.gitparser.gitbook import clean_gitbook_url, convert_gitbook_to_markdown
from mcp_server_gitparser.gitparser.github import clean_github_url, convert_repo_to_markdown
from mcp_server_gitparser.schemas import ConvertGitbookRequest, ConvertGithubRequest, ConvertResponse

router = APIRouter(tags=["Parsing"])


def generate_filename(url: str, extension: str = "md") -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.replace(".", "_")
    path = parsed.path.strip("/").replace("/", "_") if parsed.path else ""

    filename = f"{domain}_{path}" if path else domain
    filename = re.sub(r"[^\w\-_]", "", filename)
    if not filename:
        filename = "docs"
    return f"{filename}.{extension}"


def ensure_docs_dir() -> Path:
    settings = get_app_settings()
    settings.docs_path.mkdir(parents=True, exist_ok=True)
    return settings.docs_path


async def perform_parse_gitbook(url: str) -> ConvertResponse:
    cleaned_url = clean_gitbook_url(url)
    markdown_content = await convert_gitbook_to_markdown(cleaned_url)

    docs_dir = ensure_docs_dir()
    filename = generate_filename(cleaned_url, "md")
    file_path = docs_dir / filename
    file_path.write_text(markdown_content, encoding="utf-8")

    return ConvertResponse(
        success=True,
        url=cleaned_url,
        markdown=markdown_content,
        length=len(markdown_content),
        file_path=str(file_path),
    )


async def perform_parse_github(
    url: str,
    token: str | None,
    include_submodules: bool,
    include_gitignored: bool,
) -> ConvertResponse:
    cleaned_url = clean_github_url(url)
    markdown_content = await convert_repo_to_markdown(
        cleaned_url,
        token=token,
        include_submodules=include_submodules,
        include_gitignored=include_gitignored,
    )

    docs_dir = ensure_docs_dir()
    filename = generate_filename(cleaned_url, "md")
    file_path = docs_dir / filename
    file_path.write_text(markdown_content, encoding="utf-8")

    return ConvertResponse(
        success=True,
        url=cleaned_url,
        markdown=markdown_content,
        length=len(markdown_content),
        file_path=str(file_path),
    )


@router.post(
    "/parse-gitbook",
    response_model=ConvertResponse,
    operation_id="gitparser_parse_gitbook",
    summary="Parse a GitBook site into Markdown",
)
async def parse_gitbook_endpoint(request: ConvertGitbookRequest) -> ConvertResponse:
    return await perform_parse_gitbook(str(request.url))


@router.post(
    "/parse-github",
    response_model=ConvertResponse,
    operation_id="gitparser_parse_github",
    summary="Parse a GitHub repository into Markdown",
)
async def parse_github_endpoint(request: ConvertGithubRequest) -> ConvertResponse:
    return await perform_parse_github(
        url=str(request.url),
        token=request.token,
        include_submodules=request.include_submodules,
        include_gitignored=request.include_gitignored,
    )

