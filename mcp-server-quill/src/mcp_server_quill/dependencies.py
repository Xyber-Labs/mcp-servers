import logging
from typing import Annotated

from fastapi import Depends

from mcp_server_quill.config import get_app_settings
from mcp_server_quill.quill.client import QuillAPI
from mcp_server_quill.quill.search import TokenSearchAPI

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
        async def endpoint(quill_client: QuillAPI = Depends(get_quill_client)):
            ...

    """

    _quill_client: QuillAPI | None = None
    _search_client: TokenSearchAPI | None = None

    @classmethod
    def initialize(cls) -> None:
        """
        Initialize all dependencies.

        Call this once during application startup (in lifespan).
        """
        logger.info("Initializing dependencies...")

        settings = get_app_settings()

        if settings.quill__api_key:
            cls._quill_client = QuillAPI(
                api_key=settings.quill__api_key, base_url=settings.quill__base_url
            )
            logger.info("Quill API client initialized successfully.")
        else:
            logger.warning(
                "Quill API key is not configured; Quill endpoints will be unavailable."
            )

        cls._search_client = TokenSearchAPI(base_url=settings.dexscreener__base_url)
        logger.info("Token search client initialized successfully.")

        logger.info("Dependencies initialized successfully.")

    @classmethod
    async def shutdown(cls) -> None:
        """
        Shut down all dependencies gracefully.

        Call this once during application shutdown (in lifespan).
        """
        logger.info("Shutting down dependencies...")

        if cls._quill_client:
            await cls._quill_client.close()
        cls._quill_client = None

        cls._search_client = None

        logger.info("Dependencies shut down successfully.")

    @classmethod
    def get_quill_client(cls) -> QuillAPI:
        """
        Get the QuillAPI instance.

        Usage as FastAPI dependency:
            @router.post("/audit")
            async def audit(quill_client: QuillAPI = Depends(get_quill_client)):
                ...
        """
        if cls._quill_client is None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=503,
                detail="Quill API client not available. Check API key configuration.",
            )
        return cls._quill_client

    @classmethod
    def get_search_client(cls) -> TokenSearchAPI:
        """
        Get the TokenSearchAPI instance.

        Usage as FastAPI dependency:
            @router.get("/search")
            async def search(search_client: TokenSearchAPI = Depends(get_search_client)):
                ...
        """
        if cls._search_client is None:
            raise RuntimeError(
                "DependencyContainer not initialized. Call DependencyContainer.initialize() first."
            )
        return cls._search_client


# Alias the class methods for use as FastAPI dependencies
get_quill_client = DependencyContainer.get_quill_client
get_search_client = DependencyContainer.get_search_client

# Typed dependencies for FastAPI injection
QuillClientDep = Annotated[QuillAPI, Depends(get_quill_client)]
SearchClientDep = Annotated[TokenSearchAPI, Depends(get_search_client)]
