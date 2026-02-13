import logging

from mcp_server_lurky.db.database import DatabaseManager
from mcp_server_lurky.db.database import get_db_manager as create_db_manager
from mcp_server_lurky.lurky.config import get_lurky_config
from mcp_server_lurky.lurky.module import LurkyClient

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        DependencyContainer.initialize()

    Yield:
        await DependencyContainer.shutdown()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(lurky_client: LurkyClient = Depends(get_lurky_client)):
            ...

    """

    _lurky_client: LurkyClient | None = None
    _db_manager: DatabaseManager | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        config = get_lurky_config()
        cls._lurky_client = LurkyClient(config)

        # Database is optional - used for caching only
        try:
            cls._db_manager = create_db_manager()
            logger.info("Database connection established (caching enabled).")
        except Exception as e:
            logger.warning(f"Database not available, caching disabled: {e}")
            cls._db_manager = None

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        cls._lurky_client = None
        cls._db_manager = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_lurky_client(cls) -> LurkyClient:
        """
        Get the LurkyClient instance.

        Usage as FastAPI dependency:
            @router.post("/scrape")
            async def scrape(lurky_client: LurkyClient = Depends(get_lurky_client)):
                ...
        """
        if cls._lurky_client is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._lurky_client

    @classmethod
    def get_db_manager(cls) -> DatabaseManager | None:
        """
        Get the DatabaseManager instance (optional - may be None if DB unavailable).

        Usage as FastAPI dependency:
            @router.get("/spaces")
            async def get_spaces(db: DatabaseManager | None = Depends(get_db)):
                if db:
                    # use caching
                ...
        """
        return cls._db_manager


# Alias the class methods for use as FastAPI dependencies
get_lurky_client = DependencyContainer.get_lurky_client
get_db = DependencyContainer.get_db_manager
