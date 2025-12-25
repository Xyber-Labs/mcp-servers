"""
Pydantic schemas for request/response models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class VideoResponse(BaseModel):
    """Video information with transcript."""
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


class VideoSearchResponse(BaseModel):
    """Video search result without transcript."""
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


class SearchRequest(BaseModel):
    """Request model for video search with transcript extraction."""
    query: str = Field(..., description="Search query for YouTube videos", example="quantum computing")
    num_videos: int = Field(5, ge=1, le=50, description="Number of videos to process (1-50)", example=5)


class ExtractTranscriptsRequest(BaseModel):
    """Request model for extracting transcripts from video IDs."""
    video_ids: List[str] = Field(..., min_length=1, max_length=50, description="List of YouTube video IDs", example=["dQw4w9WgXcQ", "jNQXAC9IVRw"])


class SearchOnlyRequest(BaseModel):
    """Request model for video search without transcript extraction."""
    query: str = Field(..., description="Search query for YouTube videos", example="quantum computing")
    max_results: int = Field(10, ge=1, le=50, description="Maximum number of videos to return (1-50)", example=10)


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
    max_results: int
    videos: List[VideoSearchResponse]
    total_found: int

