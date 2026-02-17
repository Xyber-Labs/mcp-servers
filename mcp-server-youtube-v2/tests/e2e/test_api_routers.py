"""
Tests for REST API endpoints.
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


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

    def test_search_endpoint_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_videos_models
    ):
        """Test successful search request."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only

        mock_youtube_client.search_videos = AsyncMock(return_value=sample_videos_models)
        app.dependency_overrides[get_youtube_service_search_only] = (
            lambda: mock_youtube_client
        )

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/search", json={"query": "python tutorial", "num_videos": 2}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "python tutorial"
            assert data["max_results"] == 2
            assert len(data["videos"]) == 2
            assert data["total_found"] == 2
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_empty_results(
        self, app: FastAPI, mock_youtube_client: Mock
    ):
        """Test search endpoint with no results."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only

        mock_youtube_client.search_videos = AsyncMock(return_value=[])
        app.dependency_overrides[get_youtube_service_search_only] = (
            lambda: mock_youtube_client
        )

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/search", json={"query": "nonexistent query", "num_videos": 5}
            )

            assert response.status_code == 404
            assert "No videos found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_invalid_request(self, client: TestClient):
        """Test search endpoint with invalid request."""
        response = client.post("/hybrid/search", json={"invalid": "data"})

        assert response.status_code == 422  # Validation error

    def test_search_endpoint_default_max_results(
        self, app: FastAPI, mock_youtube_client: Mock, sample_video_model
    ):
        """Test search endpoint with default max_results."""
        from mcp_server_youtube.dependencies import get_youtube_service_search_only

        mock_youtube_client.search_videos = AsyncMock(return_value=[sample_video_model])
        app.dependency_overrides[get_youtube_service_search_only] = (
            lambda: mock_youtube_client
        )

        client = TestClient(app)
        try:
            response = client.post("/hybrid/search", json={"query": "test"})

            assert response.status_code == 200
            # Should use default max_results
            mock_youtube_client.search_videos.assert_called_once()
            call_args = mock_youtube_client.search_videos.call_args
            assert call_args[1]["max_results"] == 5  # Default from schema (num_videos default)
        finally:
            app.dependency_overrides.clear()


class TestSearchTranscriptsEndpoint:
    """Test cases for search-transcripts endpoint."""

    def test_search_transcripts_endpoint_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_videos_models, sample_transcript_result
    ):
        """Test successful search and extract transcripts request."""
        from mcp_server_youtube.dependencies import DependencyContainer, get_db_manager, get_youtube_service

        # Mock search_videos to return YouTubeSearchResult models
        mock_youtube_client.search_videos = AsyncMock(return_value=sample_videos_models)
        # Mock get_transcript_safe to return ApifyTranscriptResult
        mock_youtube_client.get_transcript_safe = AsyncMock(return_value=sample_transcript_result)

        # Create mock db manager
        mock_db = MagicMock()
        mock_db.batch_check_transcripts = Mock(return_value={})
        mock_db.batch_check_video_exists = Mock(return_value={})
        mock_db.get_video = Mock(return_value=None)
        mock_db.save_video = Mock(return_value=True)

        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        app.dependency_overrides[get_db_manager] = lambda: mock_db

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/search-transcripts",
                json={"query": "python tutorial", "num_videos": 2},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "python tutorial"
            assert data["num_videos"] == 2
            assert len(data["videos"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_search_transcripts_endpoint_no_results(
        self, app: FastAPI, mock_youtube_client: Mock
    ):
        """Test search-transcripts endpoint with no results."""
        from mcp_server_youtube.dependencies import get_db_manager, get_youtube_service

        # Mock search_videos to return empty list
        mock_youtube_client.search_videos = AsyncMock(return_value=[])

        mock_db = MagicMock()
        mock_db.batch_check_transcripts = Mock(return_value={})
        mock_db.batch_check_video_exists = Mock(return_value={})

        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        app.dependency_overrides[get_db_manager] = lambda: mock_db

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/search-transcripts",
                json={"query": "nonexistent", "num_videos": 5},
            )

            assert response.status_code == 404
            assert "No videos found" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestExtractTranscriptsEndpoint:
    """Test cases for extract-transcripts endpoint."""

    def test_extract_transcripts_endpoint_success(
        self, app: FastAPI, mock_youtube_client: Mock, sample_transcript_result
    ):
        """Test successful extract transcripts request."""
        from mcp_server_youtube.dependencies import get_db_manager, get_youtube_service

        # Mock get_transcript_safe to return ApifyTranscriptResult
        mock_youtube_client.get_transcript_safe = AsyncMock(return_value=sample_transcript_result)

        mock_db = MagicMock()
        mock_db.batch_check_transcripts = Mock(return_value={})
        mock_db.batch_check_video_exists = Mock(return_value={})
        mock_db.get_video = Mock(return_value=None)
        mock_db.save_video = Mock(return_value=True)

        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        app.dependency_overrides[get_db_manager] = lambda: mock_db

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/extract-transcripts",
                json={"video_ids": ["test_video_id", "test_video_id_2"]},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["video_ids"]) == 2
            assert len(data["videos"]) == 2
        finally:
            app.dependency_overrides.clear()

    def test_extract_transcripts_endpoint_failed_transcripts(
        self, app: FastAPI, mock_youtube_client: Mock
    ):
        """Test extract-transcripts endpoint returns results even when transcripts fail."""
        from mcp_server_youtube.dependencies import get_db_manager, get_youtube_service
        from mcp_server_youtube.youtube.api_models import ApifyTranscriptResult

        # Mock get_transcript_safe to return failed result
        failed_result = ApifyTranscriptResult(
            success=False,
            video_id="nonexistent_id",
            error="Video not found",
        )
        mock_youtube_client.get_transcript_safe = AsyncMock(return_value=failed_result)

        mock_db = MagicMock()
        mock_db.batch_check_transcripts = Mock(return_value={})
        mock_db.batch_check_video_exists = Mock(return_value={})
        mock_db.get_video = Mock(return_value=None)
        mock_db.save_video = Mock(return_value=True)

        app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
        app.dependency_overrides[get_db_manager] = lambda: mock_db

        client = TestClient(app)
        try:
            response = client.post(
                "/hybrid/extract-transcripts", json={"video_ids": ["nonexistent_id"]}
            )

            # Endpoint returns 200 with results showing failed transcripts
            assert response.status_code == 200
            data = response.json()
            assert len(data["videos"]) == 1
            assert data["videos"][0]["transcript_success"] is False
        finally:
            app.dependency_overrides.clear()

    def test_extract_transcripts_endpoint_invalid_request(self, client: TestClient):
        """Test extract-transcripts endpoint with invalid request."""
        response = client.post("/hybrid/extract-transcripts", json={"invalid": "data"})

        assert response.status_code == 422  # Validation error


# Commented out - endpoint /api/extract-transcript does not exist
# class TestExtractSingleTranscriptEndpoint:
#     """Test cases for extract-transcript (single video) endpoint."""
#
#     def test_extract_single_transcript_success(
#         self, app: FastAPI, mock_youtube_client: Mock, sample_video_data
#     ):
#         """Test successful single transcript extraction."""
#         from mcp_server_youtube.dependencies import get_youtube_service
#
#         video_with_transcript = sample_video_data.copy()
#         video_with_transcript["transcript"] = "Test transcript"
#         video_with_transcript["transcript_success"] = True
#
#         mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(
#             return_value=[video_with_transcript]
#         )
#         app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
#
#         client = TestClient(app)
#         try:
#             response = client.get("/api/extract-transcript?video_id=test_video_id")
#
#             assert response.status_code == 200
#             data = response.json()
#             assert data["video_id"] == "test_video_id"
#             assert data["transcript_success"] is True
#         finally:
#             app.dependency_overrides.clear()
#
#     def test_extract_single_transcript_missing_video_id(self, client: TestClient):
#         """Test extract-transcript endpoint without video_id parameter."""
#         response = client.get("/api/extract-transcript")
#
#         assert response.status_code == 422  # Validation error
#
#     def test_extract_single_transcript_not_found(
#         self, app: FastAPI, mock_youtube_client: Mock
#     ):
#         """Test extract-transcript endpoint when video not found."""
#         from mcp_server_youtube.dependencies import get_youtube_service
#
#         mock_youtube_client.extract_transcripts_for_video_ids = AsyncMock(
#             return_value=[]
#         )
#         app.dependency_overrides[get_youtube_service] = lambda: mock_youtube_client
#
#         client = TestClient(app)
#         try:
#             response = client.get("/api/extract-transcript?video_id=nonexistent")
#
#             assert response.status_code == 404
#         finally:
#             app.dependency_overrides.clear()
