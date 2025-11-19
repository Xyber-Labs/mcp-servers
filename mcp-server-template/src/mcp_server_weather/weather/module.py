"""
This module should be changed to match the external weather (or other) API you call, including any retry, caching, and client behavior specific to your use case.

Main responsibility: Implement the async WeatherClient and its factory, handling HTTP calls, retries, caching, and response parsing for weather data.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Literal

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from mcp_server_weather.weather.config import (
    WeatherConfig,
    get_weather_config,
)
from mcp_server_weather.weather.errors import WeatherApiError, WeatherClientError
from mcp_server_weather.weather.models import WeatherData

# --- Logger Setup --- #

# It's good practice to have a module-level logger.
# The actual configuration (level, handlers) is usually done in the main application entry point.
logger = logging.getLogger(__name__)

# --- Helper Functions --- #


def _is_retryable_exception(e: BaseException) -> bool:
    """Return True if the exception is a retryable network error."""
    return isinstance(e, (httpx.RequestError, WeatherApiError))


# --- Setup Retry Decorators --- #
retry_api_call = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=0.5, max=10),
    retry=retry_if_exception(_is_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@lru_cache(maxsize=1)
def get_weather_client() -> WeatherClient:
    """
    Get a cached instance of WeatherClient.

    Returns:
        Initialized WeatherClient instance

    Raises:
        WeatherConfigError: If configuration validation fails

    """
    config = get_weather_config()
    return WeatherClient(config)


class WeatherClient:
    """
    Weather client for fetching weather data from OpenWeatherMap API.

    Handles interaction with the OpenWeatherMap API with retry logic and caching.
    """

    API_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, config: WeatherConfig) -> None:
        """
        Initialize the WeatherClient.

        Args:
            config: Weather configuration settings

        Raises:
            WeatherConfigError: If configuration validation fails

        """
        self.config = config
        self._cache: dict[str, tuple[float, WeatherData]] = {}
        self._client: httpx.AsyncClient | None = None
        logger.info("WeatherClient initialized")

    def _ensure_client(self) -> httpx.AsyncClient:
        """
        Ensure the httpx client is initialized.

        Returns:
            An active httpx.AsyncClient instance.

        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.API_BASE_URL,
                timeout=self.config.timeout_seconds,
            )
        return self._client

    def _build_request_params(
        self,
        latitude: str,
        longitude: str,
        units: Literal["metric", "imperial"],
        api_key: str,
    ) -> dict[str, str]:
        """
        Build request parameters for OpenWeatherMap API.

        Args:
            latitude: Optional latitude override
            longitude: Optional longitude override

        Returns:
            Dictionary of request parameters

        """
        return {
            "lat": latitude,
            "lon": longitude,
            "units": units,
            "appid": api_key,
        }

    def _get_cache_key(
        self,
        latitude: str,
        longitude: str,
        units: Literal["metric", "imperial"],
        api_key: str,
    ) -> str:
        """
        Generate cache key for a location.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Cache key string including API key to avoid cross-tenant cache bleed

        """
        return f"{latitude}:{longitude}:{units}:{api_key}"

    def _get_from_cache(self, cache_key: str) -> WeatherData | None:
        """
        Try to get weather data from cache.

        Args:
            cache_key: Cache key for the location

        Returns:
            WeatherData if found and not expired, None otherwise

        """
        if not self.config.enable_caching:
            return None

        if cache_key not in self._cache:
            return None

        timestamp, data = self._cache[cache_key]
        if time.time() - timestamp > self.config.cache_ttl_seconds:
            # Cache expired
            del self._cache[cache_key]
            return None

        logger.debug(f"Cache hit for {cache_key}")
        return data

    def _store_in_cache(self, cache_key: str, data: WeatherData) -> None:
        """
        Store weather data in cache.

        Args:
            cache_key: Cache key for the location
            data: Weather data to cache

        """
        if not self.config.enable_caching:
            return

        self._cache[cache_key] = (time.time(), data)
        logger.debug(f"Stored in cache: {cache_key}")

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @retry_api_call
    async def get_weather(
        self,
        latitude: str,
        longitude: str,
        api_key: str,
        units: Literal["metric", "imperial"] = "metric",
    ) -> WeatherData:
        """
        Get weather data for a location.

        Args:
            latitude: Optional latitude override
            longitude: Optional longitude override

        Returns:
            WeatherData object with current weather information

        Raises:
            WeatherApiError: If the API request fails
            WeatherClientError: For other unexpected errors

        """
        # Use provided coordinates
        lat = latitude
        lon = longitude

        if not api_key:
            raise WeatherClientError("Weather API key header is required.")

        # Try to get from cache first
        cache_key = self._get_cache_key(lat, lon, units, api_key)
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # Build request parameters
        params = self._build_request_params(lat, lon, units, api_key)

        try:
            logger.info(f"Fetching weather data for coordinates: {lat}, {lon}")
            client = self._ensure_client()
            response = await client.get("", params=params)

            # httpx raises an exception for 4xx/5xx responses
            response.raise_for_status()

            data = response.json()

            # Check for API error responses within a 200 response
            if "cod" in data and data["cod"] != 200:
                error_msg = data.get("message", "Unknown API error")
                logger.error(f"API error: {error_msg}")
                raise WeatherApiError(f"OpenWeatherMap API error: {error_msg}")

            weather_data = WeatherData.from_api_response(data)
            self._store_in_cache(cache_key, weather_data)

            logger.info(f"Successfully retrieved weather data: {weather_data}")
            return weather_data

        except WeatherApiError:
            # Re-raise WeatherApiError as-is
            raise

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status error: {e}")
            raise WeatherApiError(
                f"OpenWeatherMap API HTTP error: {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise WeatherApiError(
                f"Failed to connect to OpenWeatherMap API: {e}"
            ) from e

        except (KeyError, IndexError) as e:
            logger.error(f"Data parsing error: {e}")
            raise WeatherClientError(f"Failed to parse weather data: {e}") from e

        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            raise WeatherClientError(
                f"Unexpected error getting weather data: {e}"
            ) from e
