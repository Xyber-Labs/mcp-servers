"""
Tests for REST API endpoints.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi.testclient import TestClient

from mcp_server_youtube.app import create_app
from mcp_server_youtube.schemas import SearchOnlyResponse, SearchTranscriptsResponse, ExtractTranscriptsResponse


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_health_endpoint_response_structure(self, client: TestClient):
        """Test health endpoint response structure."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "service" in data


class TestSearchEndpoint:
    """Test cases for search endpoint (search only, no transcripts)."""

    def test_search_endpoint_success(self, client_with_mock_youtube: TestClient, sample_videos_list):
        """Test successful search request."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.search_videos = AsyncMock(return_value=sample_videos_list)
        
        response = client_with_mock_youtube.post(
            "/api/v1/search",
            json={"query": "python tutorial", "max_results": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "python tutorial"
        assert data["max_results"] == 2
        assert len(data["videos"]) == 2
        assert data["total_found"] == 2

    def test_search_endpoint_empty_results(self, client_with_mock_youtube: TestClient):
        """Test search endpoint with no results."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.search_videos = AsyncMock(return_value=[])
        
        response = client_with_mock_youtube.post(
            "/api/v1/search",
            json={"query": "nonexistent query", "max_results": 5}
        )
        
        assert response.status_code == 404
        assert "No videos found" in response.json()["detail"]

    def test_search_endpoint_invalid_request(self, client: TestClient):
        """Test search endpoint with invalid request."""
        response = client.post(
            "/api/v1/search",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422  # Validation error

    def test_search_endpoint_default_max_results(self, client_with_mock_youtube: TestClient, sample_video_data):
        """Test search endpoint with default max_results."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.search_videos = AsyncMock(return_value=[sample_video_data])
        
        response = client_with_mock_youtube.post(
            "/api/v1/search",
            json={"query": "test"}
        )
        
        assert response.status_code == 200
        # Should use default max_results
        mock_client.search_videos.assert_called_once()
        call_args = mock_client.search_videos.call_args
        assert call_args[1]["max_results"] == 10  # Default from schema


class TestSearchTranscriptsEndpoint:
    """Test cases for search-transcripts endpoint."""

    def test_search_transcripts_endpoint_success(
        self, client_with_mock_youtube: TestClient, sample_videos_list
    ):
        """Test successful search and extract transcripts request."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        
        # Mock the search_and_get_transcripts method
        videos_with_transcripts = sample_videos_list.copy()
        videos_with_transcripts[0]["transcript"] = "Test transcript 1"
        videos_with_transcripts[0]["transcript_success"] = True
        videos_with_transcripts[1]["transcript"] = "Test transcript 2"
        videos_with_transcripts[1]["transcript_success"] = True
        
        mock_client.search_and_get_transcripts = AsyncMock(return_value=videos_with_transcripts)
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            response = client_with_mock_youtube.post(
                "/api/v1/search-transcripts",
                json={"query": "python tutorial", "num_videos": 2}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "python tutorial"
            assert data["num_videos"] == 2
            assert len(data["videos"]) == 2

    def test_search_transcripts_endpoint_no_results(self, client_with_mock_youtube: TestClient):
        """Test search-transcripts endpoint with no results."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.search_and_get_transcripts = AsyncMock(return_value=[])
        
        response = client_with_mock_youtube.post(
            "/api/v1/search-transcripts",
            json={"query": "nonexistent", "num_videos": 5}
        )
        
        assert response.status_code == 404
        assert "No videos found" in response.json()["detail"]


class TestExtractTranscriptsEndpoint:
    """Test cases for extract-transcripts endpoint."""

    def test_extract_transcripts_endpoint_success(
        self, client_with_mock_youtube: TestClient, sample_videos_list
    ):
        """Test successful extract transcripts request."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        
        videos_with_transcripts = sample_videos_list.copy()
        videos_with_transcripts[0]["transcript"] = "Test transcript 1"
        videos_with_transcripts[0]["transcript_success"] = True
        
        mock_client.extract_transcripts_for_video_ids = AsyncMock(return_value=videos_with_transcripts)
        
        with patch('mcp_server_youtube.api_routers.youtube.get_db_manager') as mock_db:
            mock_db.return_value.batch_check_transcripts = Mock(return_value={})
            
            response = client_with_mock_youtube.post(
                "/api/v1/extract-transcripts",
                json={"video_ids": ["test_video_id", "test_video_id_2"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["video_ids"]) == 2
            assert len(data["videos"]) == 2

    def test_extract_transcripts_endpoint_no_results(self, client_with_mock_youtube: TestClient):
        """Test extract-transcripts endpoint with no results."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[])
        
        response = client_with_mock_youtube.post(
            "/api/v1/extract-transcripts",
            json={"video_ids": ["nonexistent_id"]}
        )
        
        assert response.status_code == 404
        assert "No transcripts could be extracted" in response.json()["detail"]

    def test_extract_transcripts_endpoint_invalid_request(self, client: TestClient):
        """Test extract-transcripts endpoint with invalid request."""
        response = client.post(
            "/api/v1/extract-transcripts",
            json={"invalid": "data"}
        )
        
        assert response.status_code == 422  # Validation error


class TestExtractSingleTranscriptEndpoint:
    """Test cases for extract-transcript (single video) endpoint."""

    def test_extract_single_transcript_success(
        self, client_with_mock_youtube: TestClient, sample_video_data
    ):
        """Test successful single transcript extraction."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        
        video_with_transcript = sample_video_data.copy()
        video_with_transcript["transcript"] = "Test transcript"
        video_with_transcript["transcript_success"] = True
        
        mock_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[video_with_transcript])
        
        response = client_with_mock_youtube.get(
            "/api/v1/extract-transcript?video_id=test_video_id"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "test_video_id"
        assert data["transcript_success"] is True

    def test_extract_single_transcript_missing_video_id(self, client: TestClient):
        """Test extract-transcript endpoint without video_id parameter."""
        response = client.get("/api/v1/extract-transcript")
        
        assert response.status_code == 422  # Validation error

    def test_extract_single_transcript_not_found(self, client_with_mock_youtube: TestClient):
        """Test extract-transcript endpoint when video not found."""
        mock_client = client_with_mock_youtube.app.state.youtube_client
        mock_client.extract_transcripts_for_video_ids = AsyncMock(return_value=[])
        
        response = client_with_mock_youtube.get(
            "/api/v1/extract-transcript?video_id=nonexistent"
        )
        
        assert response.status_code == 404
