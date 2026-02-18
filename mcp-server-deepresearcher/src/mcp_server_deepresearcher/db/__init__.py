"""
Database package for research agent results.

Provides Postgres-backed storage for research reports.
"""
from __future__ import annotations

from mcp_server_deepresearcher.db.database import Database
from mcp_server_deepresearcher.db.models import Base, ResearchReport

__all__ = [
    "Base",
    "Database",
    "ResearchReport",
]
