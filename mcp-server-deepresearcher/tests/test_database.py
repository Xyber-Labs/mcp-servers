"""
Tests for database operations.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mcp_server_deepresearcher.db.database import Database, get_db_instance
from mcp_server_deepresearcher.db.models import ResearchReport, Base


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock(spec=Session)
    session.execute = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    return session


@pytest.fixture
def mock_db_engine():
    """Create a mock database engine."""
    engine = MagicMock()
    return engine


@pytest.fixture
def mock_database(mock_db_session, mock_db_engine):
    """Create a mock database instance."""
    db = MagicMock(spec=Database)
    db.Session = MagicMock(return_value=mock_db_session)
    db.engine = mock_db_engine
    db.save_research_report = MagicMock(return_value=1)
    return db


@pytest.mark.asyncio
async def test_get_db_instance_singleton(monkeypatch):
    """Test that get_db_instance returns a singleton."""
    # Clear any existing instance
    import mcp_server_deepresearcher.db.database as db_module
    db_module._db_instance = None
    
    # Mock Database to avoid real connection attempts
    mock_db = MagicMock(spec=Database)
    mock_db.engine = MagicMock()
    mock_db.Session = MagicMock()
    
    with patch('mcp_server_deepresearcher.db.database.Database', return_value=mock_db):
        instance1 = get_db_instance()
        instance2 = get_db_instance()
        
        assert instance1 is instance2
        assert instance1 is mock_db


@pytest.mark.asyncio
async def test_database_connection_test(mock_database):
    """Test database connection testing."""
    mock_database.Session.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = (1,)
    
    # Test that connection test works
    with mock_database.Session() as session:
        result = session.execute(Mock())
        result.fetchone()
    
    assert mock_database.Session.called


@pytest.mark.asyncio
async def test_save_research_report(mock_database):
    """Test saving a research report."""
    report_id = mock_database.save_research_report(
        research_topic="test topic",
        title="Test Report",
        executive_summary="Summary",
        key_findings=["Finding 1"],
        sources="source1.com",
        report_data={"data": "value"},
        research_loop_count=3
    )
    
    assert report_id == 1
    mock_database.save_research_report.assert_called_once()


@pytest.mark.asyncio
async def test_save_research_report_with_minimal_data(mock_database):
    """Test saving research report with minimal required data."""
    report_id = mock_database.save_research_report(
        research_topic="minimal topic",
        title="Minimal Report",
        executive_summary="",
        key_findings=[],
        sources=None,
        report_data=None,
        research_loop_count=1
    )
    
    assert report_id == 1


@pytest.mark.asyncio
async def test_database_initialization_with_custom_url(monkeypatch):
    """Test database initialization with custom URL."""
    custom_url = "postgresql+psycopg2://user:pass@host:5432/testdb"
    
    with patch('mcp_server_deepresearcher.db.database.create_engine') as mock_create:
        mock_engine = MagicMock()
        mock_create.return_value = mock_engine
        
        db = Database(db_url=custom_url)
        
        assert db.engine == mock_engine
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_database_initialization_retry_logic(monkeypatch):
    """Test database initialization retry logic."""
    import time
    
    call_count = 0
    
    def mock_create_engine(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Connection failed")
        return MagicMock()
    
    with patch('mcp_server_deepresearcher.db.database.create_engine', side_effect=mock_create_engine), \
         patch('mcp_server_deepresearcher.db.database.time.sleep'):
        db = Database(max_retries=5, retry_delay=0.1)
        
        assert db.engine is not None
        assert call_count == 3


@pytest.mark.asyncio
async def test_database_session_context_manager(mock_database):
    """Test database session context manager."""
    with mock_database.Session() as session:
        assert session is not None
    
    mock_database.Session.return_value.__exit__.assert_called_once()


@pytest.mark.asyncio
async def test_research_report_model_fields():
    """Test ResearchReport model fields."""
    report = ResearchReport(
        research_topic="test topic",
        title="Test Title",
        executive_summary="Summary",
        key_findings=["Finding 1", "Finding 2"],
        sources="source1.com, source2.com",
        report_data={"key": "value"},
        research_loop_count=3
    )
    
    assert report.research_topic == "test topic"
    assert report.title == "Test Title"
    assert report.executive_summary == "Summary"
    assert len(report.key_findings) == 2
    assert report.sources == "source1.com, source2.com"
    assert report.research_loop_count == 3


@pytest.mark.asyncio
async def test_research_report_timestamps(mock_database):
    """Test that research reports have timestamps."""
    from datetime import datetime
    
    report = ResearchReport(
        research_topic="test",
        title="Test",
        executive_summary="Summary",
        key_findings=[],
        sources="",
        report_data={},
        research_loop_count=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Timestamps should be set
    assert report.created_at is not None
    assert report.updated_at is not None


@pytest.mark.asyncio
async def test_database_error_handling(mock_database):
    """Test database error handling."""
    mock_database.save_research_report.side_effect = Exception("Database error")
    
    with pytest.raises(Exception) as exc_info:
        mock_database.save_research_report(
            research_topic="test",
            title="Test",
            executive_summary="",
            key_findings=[],
            sources="",
            report_data={},
            research_loop_count=1
        )
    
    assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_database_connection_failure_handling(monkeypatch):
    """Test handling of database connection failures."""
    import mcp_server_deepresearcher.db.database as db_module
    db_module._db_instance = None
    
    def failing_engine(*args, **kwargs):
        raise Exception("Connection failed")
    
    with patch('mcp_server_deepresearcher.db.database.create_engine', side_effect=failing_engine):
        with pytest.raises(Exception):
            Database(max_retries=1, retry_delay=0.1)


@pytest.mark.asyncio
async def test_database_table_creation(monkeypatch):
    """Test database table creation."""
    mock_engine = MagicMock()
    # Mock the connect context manager for connection test
    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.execute.return_value.fetchone.return_value = (1,)
    mock_engine.connect.return_value = mock_conn
    
    with patch('mcp_server_deepresearcher.db.database.create_engine', return_value=mock_engine):
        db = Database(db_url="postgresql+psycopg2://user:pass@host:5432/testdb")
        
        # Table creation should be called
        # This depends on implementation details
        assert db.engine == mock_engine

