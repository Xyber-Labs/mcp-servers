from __future__ import annotations

from mcp_server_together_imgen.together.client import TogetherClient


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        client = TogetherClient(settings)
        DependencyContainer.create(together_client=client)

    Yield:
        # Cleanup if needed
        DependencyContainer.clear()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(client: TogetherClient = Depends(get_together_client)):
            ...

    """

    _together_client: TogetherClient | None = None

    @classmethod
    def create(cls, *, together_client: TogetherClient) -> None:
        """Store all dependencies (call from lifespan startup)."""
        cls._together_client = together_client

    @classmethod
    def get_together_client(cls) -> TogetherClient:
        """Get the TogetherClient instance for use as FastAPI dependency."""
        if cls._together_client is None:
            raise RuntimeError(
                "DependencyContainer not created. Call DependencyContainer.create() first."
            )
        return cls._together_client

    @classmethod
    def clear(cls) -> None:
        """Clear all dependencies (call from lifespan shutdown)."""
        cls._together_client = None


get_together_client = DependencyContainer.get_together_client
