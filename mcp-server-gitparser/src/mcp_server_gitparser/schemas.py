"""Pydantic schemas for the Gitparser server."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status", examples=["ok"])
    version: str = Field(..., description="Server version", examples=["0.1.0"])


class ConvertGitbookRequest(BaseModel):
    """Request model for GitBook conversion."""

    url: HttpUrl = Field(
        ...,
        description="The URL of the GitBook to convert (query parameters will be automatically removed).",
        examples=["https://docs.gitbook.com"],
    )


class ConvertGithubRequest(BaseModel):
    """Request model for GitHub repository conversion."""

    url: HttpUrl = Field(
        ...,
        description="The GitHub repository URL to convert.",
        examples=["https://github.com/coderamp-labs/gitingest"],
    )
    token: Optional[str] = Field(None, description="GitHub Personal Access Token for private repositories.")
    include_submodules: bool = Field(False, description="Include repository submodules.")
    include_gitignored: bool = Field(False, description="Include files listed in .gitignore.")


class ConvertResponse(BaseModel):
    success: bool = Field(..., description="Whether the conversion was successful.")
    url: str = Field(..., description="The URL that was converted.")
    markdown: str = Field(..., description="The converted Markdown content.")
    length: int = Field(..., description="Length of the content in characters.")
    file_path: str = Field(..., description="Path to the saved file.")


class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for errors.")
    error: str = Field(..., description="Error message.")
    url: Optional[str] = Field(None, description="The URL that caused the error.")

