"""
Database package for research agent results.

Provides Postgres-backed storage for research reports.
"""

from __future__ import annotations

from .database import Database, get_db_instance
from .models import Base, ResearchReport

__all__ = [
    "Base",
    "Database",
    "ResearchReport",
    "get_db_instance",
]

