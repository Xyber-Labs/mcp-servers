"""
BaseModels for capturing external YouTube API responses.
"""

from pydantic import BaseModel


class YouTubeSearchResult(BaseModel):
    """BaseModel for YouTube search result from Apify YouTube Search actor."""

    id: str | None = None
    video_id: str | None = None
    display_id: str | None = None
    title: str | None = None
    channel: str | None = None
    channel_id: str | None = None
    channel_url: str | None = None
    uploader: str | None = None
    uploader_id: str | None = None
    webpage_url: str | None = None
    url: str | None = None
    link: str | None = None
    link_suffix: str | None = None
    duration: int | None = None
    view_count: int | None = None
    like_count: int | None = None
    comment_count: int | None = None
    # Normalized fields
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    upload_date: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    thumbnails: list[dict] | None = None

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
    transcript: str | None = None
    is_generated: bool | None = None
    language: str | None = None
    error: str | None = None

    @classmethod
    def from_apify_response(
        cls, video_id: str, dataset_items: list[dict]
    ) -> "ApifyTranscriptResult":
        """Create ApifyTranscriptResult from Apify dataset items."""
        if not dataset_items:
            return cls(
                success=False,
                video_id=video_id,
                error="No transcript data returned from Apify",
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
                error="No transcript segments found in Apify response",
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
                error="Could not extract text from transcript segments",
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
