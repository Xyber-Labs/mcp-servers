"""
BaseModels for capturing external YouTube API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class YouTubeSearchResult(BaseModel):
    """BaseModel for YouTube search result from Apify YouTube Search actor."""
    id: Optional[str] = None
    video_id: Optional[str] = None
    display_id: Optional[str] = None
    title: Optional[str] = None
    channel: Optional[str] = None
    channel_id: Optional[str] = None
    channel_url: Optional[str] = None
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    webpage_url: Optional[str] = None
    url: Optional[str] = None
    link: Optional[str] = None
    link_suffix: Optional[str] = None
    duration: Optional[int] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    # Normalized fields
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    upload_date: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    thumbnails: Optional[List[dict]] = None

    @classmethod
    def from_dict(cls, entry: dict) -> "YouTubeSearchResult":
        """Create YouTubeSearchResult from Apify YouTube Search actor response dictionary."""
        return cls.model_validate(entry)

    # --- Dict-like compatibility (tests + legacy callers) ---
    def __getitem__(self, key: str):
        # Prefer model fields, fall back to a dumped dict for aliases/extra keys.
        if key in self.model_fields:
            return getattr(self, key)
        return self.model_dump().get(key)

    def get(self, key: str, default=None):
        val = self.__getitem__(key)
        return default if val is None else val

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key in self.model_dump()


class ApifyTranscriptResult(BaseModel):
    """BaseModel for Apify transcript API response."""
    success: bool
    video_id: str
    transcript: Optional[str] = None
    is_generated: Optional[bool] = None
    language: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_apify_response(cls, video_id: str, dataset_items: List[dict]) -> "ApifyTranscriptResult":
        """Create ApifyTranscriptResult from Apify dataset items."""
        if not dataset_items:
            return cls(
                success=False,
                video_id=video_id,
                error="No transcript data returned from Apify"
            )

        result = dataset_items[0]
        transcript_segments = result.get("data", [])

        if not isinstance(transcript_segments, list):
            if isinstance(result, list):
                transcript_segments = result
            else:
                for key, value in result.items():
                    if isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], dict) and "text" in value[0]:
                            transcript_segments = value
                            break

        if not transcript_segments or not isinstance(transcript_segments, list):
            return cls(
                success=False,
                video_id=video_id,
                error="No transcript segments found in Apify response"
            )

        text_parts = []
        for segment in transcript_segments:
            if isinstance(segment, dict):
                text = segment.get("text", "").strip()
                if text:
                    text_parts.append(text)
            elif isinstance(segment, str):
                text_parts.append(segment.strip())

        transcript_text = " ".join(text_parts)

        if not transcript_text:
            return cls(
                success=False,
                video_id=video_id,
                error="Could not extract text from transcript segments"
            )

        return cls(
            success=True,
            video_id=video_id,
            transcript=transcript_text,
            is_generated=None,
            language=None,
        )

    # --- Dict-like compatibility (tests + legacy callers) ---
    def __getitem__(self, key: str):
        if key in self.model_fields:
            return getattr(self, key)
        return self.model_dump().get(key)

    def get(self, key: str, default=None):
        val = self.__getitem__(key)
        return default if val is None else val

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key in self.model_dump()

