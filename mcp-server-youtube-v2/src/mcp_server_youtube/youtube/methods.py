"""
Database manager for YouTube video caching.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from mcp_server_youtube.config import get_app_settings
from mcp_server_youtube.youtube.models import Base, YouTubeVideo

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for YouTube video caching."""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file. Defaults to config value.
        """
        settings = get_app_settings()
        self.db_path = db_path or settings.db_path
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.debug(f"Database tables created/verified at {self.db_path}")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def get_video(self, video_id: str) -> Optional[YouTubeVideo]:
        """
        Get video from database by video_id.

        Args:
            video_id: YouTube video ID

        Returns:
            YouTubeVideo object if found, None otherwise
        """
        session = self.get_session()
        try:
            video = session.query(YouTubeVideo).filter_by(video_id=video_id).first()
            return video
        except SQLAlchemyError as e:
            logger.error(f"Error getting video {video_id} from database: {e}")
            return None
        finally:
            session.close()

    def has_transcript(self, video_id: str) -> bool:
        """
        Check if video has a successful transcript in database.

        Args:
            video_id: YouTube video ID

        Returns:
            True if transcript exists and is successful, False otherwise
        """
        video = self.get_video(video_id)
        if video and video.transcript_success and video.transcript:
            return True
        return False

    def save_video(self, video_data: Dict) -> bool:
        """
        Save or update video data in database.
        Automatically calculates transcript_length if transcript is provided.

        Args:
            video_data: Dictionary containing video information

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session()
        try:
            video_id = video_data.get("video_id")
            if not video_id:
                logger.warning("Cannot save video: missing video_id")
                return False

            if "transcript" in video_data and "transcript_length" not in video_data:
                transcript = video_data.get("transcript")
                if transcript:
                    video_data["transcript_length"] = len(transcript)
                else:
                    video_data["transcript_length"] = 0

            existing_video = session.query(YouTubeVideo).filter_by(video_id=video_id).first()

            if existing_video:
                for key, value in video_data.items():
                    if hasattr(existing_video, key):
                        setattr(existing_video, key, value)
                logger.debug(f"Updated video {video_id} in database")
            else:
                video = YouTubeVideo(**video_data)
                session.add(video)
                logger.debug(f"Saved new video {video_id} to database")

            session.commit()
            return True
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving video to database: {e}")
            return False
        finally:
            session.close()

    def batch_get_videos(self, video_ids: List[str]) -> Dict[str, Optional[YouTubeVideo]]:
        """
        Get multiple videos from database.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dictionary mapping video_id to YouTubeVideo object (or None if not found)
        """
        session = self.get_session()
        try:
            videos = session.query(YouTubeVideo).filter(YouTubeVideo.video_id.in_(video_ids)).all()
            result = {video.video_id: video for video in videos}
            for video_id in video_ids:
                if video_id not in result:
                    result[video_id] = None
            return result
        except SQLAlchemyError as e:
            logger.error(f"Error batch getting videos from database: {e}")
            return {video_id: None for video_id in video_ids}
        finally:
            session.close()

    def batch_check_transcripts(self, video_ids: List[str]) -> Dict[str, bool]:
        """
        Check which videos have transcripts in database.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dictionary mapping video_id to boolean (True if transcript exists)
        """
        videos = self.batch_get_videos(video_ids)
        return {
            video_id: (
                video is not None and video.transcript_success and video.transcript is not None
            )
            for video_id, video in videos.items()
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager

