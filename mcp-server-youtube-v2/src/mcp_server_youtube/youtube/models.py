from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    func,
)
from sqlalchemy.orm import declarative_base

# Define the base class for declarative class definitions
Base = declarative_base()


class YouTubeVideo(Base):
    """
    YouTube Video with metadata and transcript
    Stores video information, metadata, and transcripts for caching
    """

    __tablename__ = "youtube_videos"

    # --- Primary Key ---
    video_id = Column(String(255), primary_key=True)

    # --- Video Information ---
    title = Column(String(500), nullable=True)
    channel = Column(String(255), nullable=True)
    channel_id = Column(String(255), nullable=True)
    channel_url = Column(Text, nullable=True)
    video_url = Column(Text, nullable=True)

    # --- Metadata ---
    duration = Column(Integer, nullable=True)  # Duration in seconds
    views = Column(Integer, nullable=True)
    likes = Column(Integer, nullable=True)
    comments = Column(Integer, nullable=True)
    upload_date = Column(String(50), nullable=True)  # Format: YYYY-MM-DD
    description = Column(Text, nullable=True)
    thumbnail = Column(Text, nullable=True)

    # --- Transcript Information ---
    transcript_success = Column(Boolean, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_length = Column(Integer, nullable=True)  # Length of transcript in characters
    error = Column(Text, nullable=True)
    is_auto_generated = Column(Boolean, nullable=True)
    language = Column(String(10), nullable=True)

    # --- Timestamps ---
    fetched_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<YouTubeVideo(video_id='{self.video_id}', title='{self.title}', transcript_success={self.transcript_success})>"

