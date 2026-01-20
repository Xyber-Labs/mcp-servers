"""
Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class VideoResponse(BaseModel):
    """Video information with transcript."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Example Video",
                "channel": "Example Channel",
                "video_url": "https://www.youtube.com/watch?v=example",
                "video_id": "example",
                "likes": 1000,
                "transcript_success": True,
                "transcript_length": 5000,
                "transcript_preview": "This is a preview of the transcript..."
            }
        }
    )
    
    title: str
    channel: str
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    video_url: str
    video_id: str
    duration: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    upload_date: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    transcript_success: bool
    transcript: Optional[str] = None
    transcript_length: Optional[int] = None
    transcript_preview: Optional[str] = Field(None, description="First 300 characters of transcript")
    error: Optional[str] = None
    is_auto_generated: Optional[bool] = None
    language: Optional[str] = None

    @classmethod
    def from_video(cls, video: dict, include_transcript_preview: bool = True) -> "VideoResponse":
        """Create VideoResponse from video dictionary."""
        transcript_preview = None
        if include_transcript_preview and video.get("transcript"):
            transcript = video["transcript"]
            transcript_preview = (
                transcript[:300] + "..." if len(transcript) > 300 else transcript
            )

        video_url = (
            video.get("video_url")
            or video.get("url")
            or video.get("link")
            or f"https://www.youtube.com/watch?v={video.get('video_id') or video.get('id')}"
        )

        prepared = {
            "title": video.get("title", "Unknown"),
            "channel": video.get("channel", "Unknown"),
            "channel_id": video.get("channel_id"),
            "channel_url": video.get("channel_url"),
            "video_url": video_url,
            "video_id": video.get("video_id") or video.get("id", ""),
            "duration": video.get("duration"),
            "views": video.get("views"),
            "likes": video.get("likes"),
            "comments": video.get("comments"),
            "upload_date": video.get("upload_date"),
            "description": video.get("description"),
            "thumbnail": video.get("thumbnail"),
            "transcript_success": video.get("transcript_success", False),
            "transcript": video.get("transcript"),
            "transcript_length": video.get("transcript_length"),
            "transcript_preview": transcript_preview,
            "error": video.get("error"),
            "is_auto_generated": video.get("is_auto_generated"),
            "language": video.get("language"),
            **video,
        }
        return cls.model_validate(prepared)


class VideoSearchResponse(BaseModel):
    """Video search result without transcript."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Example Video",
                "channel": "Example Channel",
                "video_url": "https://www.youtube.com/watch?v=example",
                "video_id": "example",
                "likes": 1000
            }
        }
    )
    
    title: str
    channel: str
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    video_url: str
    video_id: str
    duration: Optional[int] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    upload_date: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None

    @classmethod
    def from_video(cls, video: dict) -> "VideoSearchResponse":
        """Create VideoSearchResponse from video dictionary."""
        video_url = (
            video.get("url")
            or video.get("link")
            or f"https://www.youtube.com/watch?v={video.get('id') or video.get('video_id')}"
        )
        prepared = {
            "title": video.get("title", "Unknown"),
            "channel": video.get("channel", "Unknown"),
            "channel_id": video.get("channel_id"),
            "channel_url": video.get("channel_url"),
            "video_url": video_url,
            "video_id": video.get("id") or video.get("video_id", ""),
            "duration": video.get("duration"),
            "views": video.get("views"),
            "likes": video.get("likes"),
            "comments": video.get("comments"),
            "upload_date": video.get("upload_date"),
            "description": video.get("description"),
            "thumbnail": video.get("thumbnail"),
            **video,
        }
        return cls.model_validate(prepared)


class SearchVideosRequest(BaseModel):
    """Request model for video search."""
    query: str = Field(..., description="Search query for YouTube videos")
    num_videos: int = Field(5, ge=1, le=50, description="Number of videos to process (1-50)")
    include_transcripts: bool = Field(False, description="Whether to include transcripts in the response")
    max_results: int | None = Field(None, ge=1, le=50, description="Alias for num_videos (deprecated)")
    
    # Apify YouTube Search Actor parameters
    exclude_shorts: bool = Field(False, description="Exclude YouTube Shorts from results")
    shorts_only: bool = Field(False, description="Return only YouTube Shorts")
    upload_date_filter: str = Field("", description="Filter by upload date (e.g., 'today', 'week', 'month', 'year')")
    sort_by: str = Field("relevance", description="Sort order: 'relevance', 'rating', 'upload_date', 'view_count'")
    sleep_interval: int = Field(2, ge=0, le=10, description="Sleep interval between requests (seconds)")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum number of retries for failed requests")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "quantum computing",
                "num_videos": 5,
                "include_transcripts": False,
                "exclude_shorts": False,
                "shorts_only": False,
                "upload_date_filter": "",
                "sort_by": "relevance",
                "sleep_interval": 2,
                "max_retries": 3
            }
        }
    )

    def __init__(self, **data):
        """Handle backward compatibility with max_results."""
        if "max_results" in data and "num_videos" not in data:
            data["num_videos"] = data.pop("max_results")
        super().__init__(**data)


class ExtractTranscriptsRequest(BaseModel):
    """Request model for extracting transcripts from video IDs."""
    video_ids: List[str] = Field(..., min_length=1, max_length=50, description="List of YouTube video IDs")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "video_ids": ["dQw4w9WgXcQ", "jNQXAC9IVRw"]
            }
        }
    )


class SearchTranscriptsResponse(BaseModel):
    """Response model for search and extract transcripts endpoint."""
    query: str
    num_videos: int
    videos: List[VideoResponse]
    total_found: int
    cached_count: int


class ExtractTranscriptsResponse(BaseModel):
    """Response model for extract transcripts endpoint."""
    video_ids: List[str]
    videos: List[VideoResponse]
    total_processed: int
    cached_count: int


class SearchOnlyResponse(BaseModel):
    """Response model for search only endpoint."""
    query: str
    max_results: int  # Keep for backward compatibility
    num_videos: int | None = None  # New field
    videos: List[VideoSearchResponse]
    total_found: int

