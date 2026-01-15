"""
Database layer for storing research agent results in Postgres.

Handles connection, table creation, and research report storage operations.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from mcp_server_deepresearcher.db.models import Base, ResearchReport

logger = logging.getLogger(__name__)

_db_instance: Database | None = None


def get_db_instance() -> Database:
    """Get or create the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance


class Database:
    """
    Database wrapper for research agent results.

    Handles connection, table creation, and report storage operations.
    """

    def __init__(
        self,
        db_url: str | None = None,
        max_retries: int = 30,
        retry_delay: int = 2,
    ):
        """
        Initialize database connection with retry logic.

        Args:
            db_url: Optional database URL. If None, reads from config
            max_retries: Maximum number of connection retry attempts
            retry_delay: Initial delay between retries in seconds (exponential backoff)
        """
        if db_url is None:
            from mcp_server_deepresearcher.deepresearcher.config import Settings
            settings = Settings()
            db_config = settings.database
            db_url = db_config.DATABASE_URL
            if not db_url:
                raise RuntimeError(
                    "DATABASE_URL not configured. Set it in .env or environment variables."
                )

        self.engine = None
        self.Session: sessionmaker[Session] | None = None

        # Retry connection with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")

                # Create database engine with connection pooling
                self.engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={
                        "connect_timeout": 10,
                        "options": "-c statement_timeout=30000",
                    },
                )

                # Test connection
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()

                logger.info("Database connection test successful!")

                # Create session factory
                self.Session = sessionmaker(bind=self.engine)

                # Create tables if they don't exist
                try:
                    Base.metadata.create_all(self.engine)
                    logger.info("Database tables verified/created successfully!")
                except Exception as table_error:
                    logger.warning(
                        f"Could not create/verify tables (this is OK if migrations handle it): "
                        f"{str(table_error)[:200]}"
                    )

                logger.info("Database connection established successfully!")
                return

            except OperationalError as e:
                if attempt < max_retries - 1:
                    wait_time = min(retry_delay * (2 ** min(attempt, 3)), 10)
                    logger.warning(
                        f"Database connection failed (attempt {attempt + 1}/{max_retries}): "
                        f"{str(e)[:200]}"
                    )
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = min(retry_delay * (2 ** min(attempt, 3)), 10)
                    logger.warning(
                        f"Unexpected error connecting to database "
                        f"(attempt {attempt + 1}/{max_retries}): {str(e)[:200]}"
                    )
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                    raise

    def save_research_report(
        self,
        research_topic: str,
        title: str,
        executive_summary: str,
        key_findings: list[str],
        sources: str | None = None,
        report_data: dict[str, Any] | None = None,
        research_loop_count: int = 1,
    ) -> int:
        """
        Save a research report to the database.

        Args:
            research_topic: The research topic that was investigated
            title: Report title
            executive_summary: Executive summary text
            key_findings: List of key findings
            sources: Formatted sources string (optional)
            report_data: Full report JSON data (optional)
            research_loop_count: Number of research loops performed

        Returns:
            The ID of the created report
        """
        if not self.Session:
            raise RuntimeError("Database session not initialized")

        with self.Session() as session:
            report = ResearchReport(
                research_topic=research_topic,
                title=title,
                executive_summary=executive_summary,
                key_findings=key_findings,
                sources=sources,
                report_data=report_data,
                research_loop_count=research_loop_count,
            )
            session.add(report)
            session.commit()
            session.refresh(report)
            
            logger.info(
                f"Saved research report to database (id={report.id}, "
                f"topic='{research_topic[:50]}...', title='{title[:50]}...')"
            )
            return report.id

    def get_research_report(self, report_id: int) -> ResearchReport | None:
        """
        Retrieve a research report by ID.

        Args:
            report_id: The ID of the report to retrieve

        Returns:
            ResearchReport object if found, None otherwise
        """
        if not self.Session:
            return None

        with self.Session() as session:
            report = session.query(ResearchReport).filter(ResearchReport.id == report_id).first()
            return report

    def get_reports_by_topic(
        self, research_topic: str, limit: int = 10
    ) -> list[ResearchReport]:
        """
        Retrieve research reports by topic, ordered by creation date (newest first).

        Args:
            research_topic: The research topic to filter by
            limit: Maximum number of reports to return

        Returns:
            List of ResearchReport objects
        """
        if not self.Session:
            return []

        with self.Session() as session:
            reports = (
                session.query(ResearchReport)
                .filter(ResearchReport.research_topic == research_topic)
                .order_by(ResearchReport.created_at.desc())
                .limit(limit)
                .all()
            )
            return reports

    def get_recent_reports(self, limit: int = 10) -> list[ResearchReport]:
        """
        Retrieve the most recent research reports across all topics.

        Args:
            limit: Maximum number of reports to return

        Returns:
            List of ResearchReport objects ordered by creation date (newest first)
        """
        if not self.Session:
            return []

        with self.Session() as session:
            reports = (
                session.query(ResearchReport)
                .order_by(ResearchReport.created_at.desc())
                .limit(limit)
                .all()
            )
            return reports

