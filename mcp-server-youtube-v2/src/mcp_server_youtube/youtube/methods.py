"""
Database manager for YouTube video caching.
"""

import logging
from typing import Dict, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from mcp_server_youtube.config import DatabaseConfig
from mcp_server_youtube.youtube.models import Base, YouTubeVideo

logger = logging.getLogger(__name__)


class NullDatabaseManager:
    """
    No-op DB manager used when Postgres is unavailable.
    This lets the server run in a degraded mode (no caching) instead of crashing.
    """

    def get_session(self) -> Session:  # pragma: no cover
        raise RuntimeError("Database is unavailable (NullDatabaseManager).")

    def get_video(self, video_id: str) -> Optional[YouTubeVideo]:
        return None

    def has_transcript(self, video_id: str) -> bool:
        return False

    def save_video(self, video_data: Dict) -> bool:
        return False

    def batch_get_videos(self, video_ids: List[str]) -> Dict[str, Optional[YouTubeVideo]]:
        return {video_id: None for video_id in video_ids}

    def batch_check_transcripts(self, video_ids: List[str]) -> Dict[str, bool]:
        return {video_id: False for video_id in video_ids}
    
    def video_exists(self, video_id: str) -> bool:
        return False
    
    def batch_check_video_exists(self, video_ids: List[str]) -> Dict[str, bool]:
        return {video_id: False for video_id in video_ids}


class DatabaseManager:
    """Manages database connections and operations for YouTube video caching."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: PostgreSQL connection URL. Defaults to DatabaseConfig.DATABASE_URL.
        
        Raises:
            ValueError: If DATABASE_URL is not configured or connection cannot be established.
        """
        if database_url is None:
            db_config = DatabaseConfig()
            database_url = db_config.DATABASE_URL
        
        if not database_url:
            raise ValueError(
                "DATABASE_URL is required. Set DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, and DB_PORT environment variables."
            )
        
        logger.info(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else '***'}")
        
        try:
            self.engine = create_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,  # Verify connections before using
            )
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Test connection immediately
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info("Successfully connected to database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise ValueError(
                f"Database connection failed. Please verify DATABASE_URL and ensure PostgreSQL is running. Error: {e}"
            ) from e

        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created/verified")
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
        Also checks if video exists (even with failed transcript) to avoid retrying.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dictionary mapping video_id to boolean (True if transcript exists and is successful)
        """
        videos = self.batch_get_videos(video_ids)
        return {
            video_id: (
                video is not None and video.transcript_success and video.transcript is not None
            )
            for video_id, video in videos.items()
        }
    
    def video_exists(self, video_id: str) -> bool:
        """
        Check if video exists in database (regardless of transcript success).

        Args:
            video_id: YouTube video ID

        Returns:
            True if video exists in database, False otherwise
        """
        video = self.get_video(video_id)
        return video is not None
    
    def batch_check_video_exists(self, video_ids: List[str]) -> Dict[str, bool]:
        """
        Check which videos exist in database (regardless of transcript success).
        Used to avoid retrying transcript extraction for videos we've already attempted.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dictionary mapping video_id to boolean (True if video exists in DB)
        """
        videos = self.batch_get_videos(video_ids)
        return {
            video_id: video is not None
            for video_id, video in videos.items()
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get or create global database manager instance."""
    global _db_manager
    if _db_manager is None:
        try:
            _db_manager = DatabaseManager()
        except Exception as e:
            logger.warning(
                "Postgres unavailable; starting without caching. Error: %s", e
            )
            _db_manager = NullDatabaseManager()  # type: ignore[assignment]
    return _db_manager

