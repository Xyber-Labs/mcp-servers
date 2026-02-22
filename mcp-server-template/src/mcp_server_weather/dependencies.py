"""
This module should be changed to include your server's dependencies like API clients, database session managers, etc.

Main responsibility: Provide a single place to access all service clients used by the application.
Lifecycle is managed externally (in lifespan) following dependency injection principles.
"""

from __future__ import annotations

from mcp_server_weather.weather import WeatherClient


class DependencyContainer:
    """
    Centralized container for all application dependencies.

    Usage:
        # In app.py lifespan:
        client = WeatherClient(config)
        DependencyContainer.create(weather_client=client)

    Yield:
        await client.close()
        DependencyContainer.clear()

        # In route handlers via Depends():
        @router.post("/endpoint")
        async def endpoint(client: WeatherClient = Depends(get_weather_client)):
            ...

    """

    _weather_client: WeatherClient | None = None

    @classmethod
    def create(cls, *, weather_client: WeatherClient) -> None:
        """Store all dependencies (call from lifespan startup)."""
        cls._weather_client = weather_client

    @classmethod
    def get_weather_client(cls) -> WeatherClient:
        """Get the WeatherClient instance for use as FastAPI dependency."""
        if cls._weather_client is None:
            raise RuntimeError(
                "DependencyContainer not created. Call DependencyContainer.create() first."
            )
        return cls._weather_client

    @classmethod
    def clear(cls) -> None:
        """Clear all dependencies (call from lifespan shutdown)."""
        cls._weather_client = None


get_weather_client = DependencyContainer.get_weather_client
