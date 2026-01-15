"""
REST-only endpoints for retrieving research reports from the database.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from mcp_server_deepresearcher.db.database import get_db_instance

logger = logging.getLogger(__name__)
router = APIRouter()


class ReportResponse(BaseModel):
    """Response model for a research report."""

    id: int
    research_topic: str
    title: str
    executive_summary: str
    key_findings: list[str]
    sources: Optional[str] = None
    report_data: Optional[dict] = None
    research_loop_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReportsListResponse(BaseModel):
    """Response model for a list of reports."""

    reports: list[ReportResponse]
    count: int
    limit: int


@router.get(
    "/reports",
    tags=["Reports"],
    operation_id="get_reports",
    response_model=ReportsListResponse,
)
async def get_reports(
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of reports to retrieve (1-100)",
    ),
    topic: Optional[str] = Query(
        default=None,
        description="Filter reports by research topic",
    ),
) -> ReportsListResponse:
    """
    Retrieve research reports from the database.

    Returns the most recent reports, optionally filtered by topic.
    If topic is provided, returns reports matching that topic.
    If topic is not provided, returns the most recent reports across all topics.

    Args:
        limit: Maximum number of reports to retrieve (default: 10, max: 100)
        topic: Optional topic filter to retrieve reports for a specific research topic

    Returns:
        List of research reports with metadata
    """
    logger.info(f"Retrieving reports: limit={limit}, topic={topic}")

    try:
        db = get_db_instance()

        if topic:
            # Get reports by topic
            reports = db.get_reports_by_topic(research_topic=topic, limit=limit)
            logger.info(f"Retrieved {len(reports)} reports for topic '{topic}'")
        else:
            # Get most recent reports across all topics
            reports = db.get_recent_reports(limit=limit)
            logger.info(f"Retrieved {len(reports)} most recent reports")

        # Convert SQLAlchemy models to Pydantic models
        report_responses = [
            ReportResponse(
                id=report.id,
                research_topic=report.research_topic,
                title=report.title,
                executive_summary=report.executive_summary,
                key_findings=report.key_findings,
                sources=report.sources,
                report_data=report.report_data,
                research_loop_count=report.research_loop_count,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat(),
            )
            for report in reports
        ]

        return ReportsListResponse(
            reports=report_responses,
            count=len(report_responses),
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error retrieving reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}",
        )


@router.get(
    "/reports/by-topic/{topic}",
    tags=["Reports"],
    operation_id="get_reports_by_topic",
    response_model=ReportsListResponse,
)
async def get_reports_by_topic(
    topic: str,
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of reports to retrieve (1-100)",
    ),
) -> ReportsListResponse:
    """
    Retrieve research reports for a specific topic.

    Args:
        topic: The research topic to filter by
        limit: Maximum number of reports to retrieve (default: 10, max: 100)

    Returns:
        List of research reports for the specified topic
    """
    logger.info(f"Retrieving reports for topic '{topic}': limit={limit}")

    try:
        db = get_db_instance()
        reports = db.get_reports_by_topic(research_topic=topic, limit=limit)

        if not reports:
            logger.info(f"No reports found for topic '{topic}'")
            return ReportsListResponse(reports=[], count=0, limit=limit)

        # Convert SQLAlchemy models to Pydantic models
        report_responses = [
            ReportResponse(
                id=report.id,
                research_topic=report.research_topic,
                title=report.title,
                executive_summary=report.executive_summary,
                key_findings=report.key_findings,
                sources=report.sources,
                report_data=report.report_data,
                research_loop_count=report.research_loop_count,
                created_at=report.created_at.isoformat(),
                updated_at=report.updated_at.isoformat(),
            )
            for report in reports
        ]

        logger.info(f"Retrieved {len(report_responses)} reports for topic '{topic}'")
        return ReportsListResponse(
            reports=report_responses,
            count=len(report_responses),
            limit=limit,
        )

    except Exception as e:
        logger.error(f"Error retrieving reports for topic '{topic}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve reports: {str(e)}",
        )


@router.get(
    "/reports/{report_id}",
    tags=["Reports"],
    operation_id="get_report_by_id",
    response_model=ReportResponse,
)
async def get_report_by_id(report_id: int) -> ReportResponse:
    """
    Retrieve a specific research report by ID.

    Args:
        report_id: The ID of the report to retrieve

    Returns:
        The research report with the specified ID

    Raises:
        HTTPException: If the report is not found
    """
    logger.info(f"Retrieving report with ID {report_id}")

    try:
        db = get_db_instance()
        report = db.get_research_report(report_id=report_id)

        if not report:
            logger.warning(f"Report with ID {report_id} not found")
            raise HTTPException(
                status_code=404,
                detail=f"Report with ID {report_id} not found",
            )

        return ReportResponse(
            id=report.id,
            research_topic=report.research_topic,
            title=report.title,
            executive_summary=report.executive_summary,
            key_findings=report.key_findings,
            sources=report.sources,
            report_data=report.report_data,
            research_loop_count=report.research_loop_count,
            created_at=report.created_at.isoformat(),
            updated_at=report.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve report: {str(e)}",
        )

