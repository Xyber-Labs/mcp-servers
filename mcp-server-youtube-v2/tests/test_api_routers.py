"""
Tests for REST API endpoints.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_youtube.app import create_app
from mcp_server_youtube.schemas import SearchOnlyResponse, SearchTranscriptsResponse, ExtractTranscriptsResponse


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_health_endpoint_response_structure(self, client: TestClient):
        """Test health endpoint response structure."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "service" in data


class TestSearchEndpoint:
    """Test cases for search endpoint (search only, no transcripts)."""

    def test_search_endpoint_success(self, app: FastAPI, mock_youtube_client: Mock, sample_videos_list):
        """Test successful search request."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only
        
        mock_youtube_client.search_videos = AsyncMock(return_value=sample_videos_list)
        app.dependency_overrides[get_youtube_service_search_only] = lambda: mock_youtube_client
        
        client = TestClient(app)
        try:
            response = client.post(
                "/api/search",
                json={"query": "python tutorial", "max_results": 2}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "python tutorial"
            assert data["max_results"] == 2
            assert len(data["videos"]) == 2
            assert data["total_found"] == 2
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_empty_results(self, app: FastAPI, mock_youtube_client: Mock):
        """Test search endpoint with no results."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only
        
        mock_youtube_client.search_videos = AsyncMock(return_value=[])
        app.dependency_overrides[get_youtube_service_search_only] = lambda: mock_youtube_client
        
        client = TestClient(app)
        try:
            response = client.post(
                "/api/search",
                json={"query": "nonexistent query", "max_results": 5}
            )
            
            assert response.status_code == 404
            assert "No videos found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_invalid_request(self, client: TestClient):
        """Test search endpoint with invalid request."""
        response = client.post(
            "/api/search",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422  # Validation error

    def test_search_endpoint_default_max_results(self, app: FastAPI, mock_youtube_client: Mock, sample_video_data):
        """Test search endpoint with default max_results."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only
        
        mock_youtube_client.search_videos = AsyncMock(return_value=[sample_video_data])
        app.dependency_overrides[get_youtube_service_search_only] = lambda: mock_youtube_client
        
        client = TestClient(app)
        try:
            response = client.post(
                "/api/search",
                json={"query": "test"}
            )
            
            assert response.status_code == 200
            # Should use default max_results
            mock_youtube_client.search_videos.assert_called_once()
            call_args = mock_youtube_client.search_videos.call_args
            assert call_args[1]["max_results"] == 10  # Default from schema
        finally:
            app.dependency_overrides.clear()


class TestSearchTranscriptsEndpoint:
    """Test cases for search-transcripts endpoint."""

    def test_search_transcripts_endpoint_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_videos_list
    ):
        """Test successful search and extract transcripts request."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        # Mock the search_and_get_transcripts method
        videos_with_transcripts = sample_videos_list.copy()
        videos_with_transcripts[0]["transcript"] = "Test transcript 1"
        videos_with_transcripts[0]["transcript_success"] = True
        videos_with_transcripts[1]["transcript"] = "Test transcript 2"
        videos_with_transcripts[1]["transcript_success"] = True
        
        mock_youtube_client.search_and_get_transcripts = AsyncMock(return_value=videos_with_transcripts)
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            client = TestClient(app)
            try:
                response = client.post(
                    "/api/search-transcripts",
                    json={"query": "python tutorial", "num_videos": 2}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["query"] == "python tutorial"
                assert data["num_videos"] == 2
                assert len(data["videos"]) == 2
            finally:
                app.dependency_overrides.clear()

    def test_search_transcripts_endpoint_no_results(self, app: FastAPI, mock_youtube_client: Mock):
        """Test search-transcripts endpoint with no results."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        mock_youtube_client.search_and_get_transcripts = AsyncMock(return_value=[])
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            client = TestClient(app)
            try:
                response = client.post(
                    "/api/search-transcripts",
                    json={"query": "nonexistent", "num_videos": 5}
                )
                
                assert response.status_code == 404
                assert "No videos found" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()


class TestExtractTranscriptsEndpoint:
    """Test cases for extract-transcripts endpoint."""

    def test_extract_transcripts_endpoint_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_videos_list
    ):
        """Test successful extract transcripts request."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        videos_with_transcripts = sample_videos_list.copy()
        videos_with_transcripts[0]["transcript"] = "Test transcript 1"
        videos_with_transcripts[0]["transcript_success"] = True
        
        mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(return_value=videos_with_transcripts)
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            client = TestClient(app)
            try:
                response = client.post(
                    "/api/extract-transcripts",
                    json={"video_ids": ["test_video_id", "test_video_id_2"]}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["video_ids"]) == 2
                assert len(data["videos"]) == 2
            finally:
                app.dependency_overrides.clear()

    def test_extract_transcripts_endpoint_no_results(self, app: FastAPI, mock_youtube_client: Mock):
        """Test extract-transcripts endpoint with no results."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[])
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            client = TestClient(app)
            try:
                response = client.post(
                    "/api/extract-transcripts",
                    json={"video_ids": ["nonexistent_id"]}
                )
                
                assert response.status_code == 404
                assert "No transcripts could be extracted" in response.json()["detail"]
            finally:
                app.dependency_overrides.clear()

    def test_extract_transcripts_endpoint_invalid_request(self, client: TestClient):
        """Test extract-transcripts endpoint with invalid request."""
        response = client.post(
            "/api/extract-transcripts",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422  # Validation error


class TestExtractSingleTranscriptEndpoint:
    """Test cases for extract-transcript (single video) endpoint."""

    def test_extract_single_transcript_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_video_data
    ):
        """Test successful single transcript extraction."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        video_with_transcript = sample_video_data.copy()
        video_with_transcript["transcript"] = "Test transcript"
        video_with_transcript["transcript_success"] = True
        
        mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[video_with_transcript])
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        client = TestClient(app)
        try:
            response = client.get(
                "/api/extract-transcript?video_id=test_video_id"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["video_id"] == "test_video_id"
            assert data["transcript_success"] is True
        finally:
            app.dependency_overrides.clear()

    def test_extract_single_transcript_missing_video_id(self, client: TestClient):
        """Test extract-transcript endpoint without video_id parameter."""
        response = client.get("/api/extract-transcript")
        
        assert response.status_code == 422  # Validation error

    def test_extract_single_transcript_not_found(self, app: FastAPI, mock_youtube_client: Mock):
        """Test extract-transcript endpoint when video not found."""
        from mcp_server_youtube.dependencies import get_youtube_service
        
        mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[])
        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        
        client = TestClient(app)
        try:
            response = client.get(
                "/api/extract-transcript?video_id=nonexistent"
            )
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()
