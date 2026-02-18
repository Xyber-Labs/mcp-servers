"""
E2E smoke tests for MCP-only endpoints.

Test coverage:
- geolocate_city (free MCP tool)
- get_weather_analysis (priced MCP tool)
"""

from __future__ import annotations

import pytest

from mcp_server_weather.schemas import GeolocationResponse, WeatherAnalysisResponse
from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    call_mcp_tool_with_client,
    initialize_mcp_session,
    initialize_mcp_session_with_client,
    negotiate_mcp_session_id,
    negotiate_mcp_session_id_with_client,
    parse_mcp_response,
)


# =============================================================================
# geolocate_city - Free MCP tool
# =============================================================================


async def test_mcp_geolocate_city_mcp() -> None:
    """Geolocate_city MCP tool (always free)."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="geolocate_city",
        arguments={"city": "Tokyo"},
        session_id=session_id,
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    geo_data = GeolocationResponse(**result_data)
    assert geo_data.city == "Tokyo"
    assert geo_data.latitude == 35.6762
    assert geo_data.longitude == 139.6503


# =============================================================================
# get_weather_analysis - Priced MCP tool
# =============================================================================


@pytest.mark.payment_off
async def test_mcp_weather_analysis_mcp_pricing_off() -> None:
    """Priced MCP tool works without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_weather_analysis",
        arguments={"city": "London"},
        session_id=session_id,
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    analysis_data = WeatherAnalysisResponse(**result_data)
    assert analysis_data.analysis
    assert "London" in analysis_data.analysis or "weather" in analysis_data.analysis.lower()


@pytest.mark.payment_on
async def test_mcp_weather_analysis_mcp_no_payment() -> None:
    """Priced MCP tool returns 402 when PRICING_MODE=on and no payment provided."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="get_weather_analysis",
        arguments={"city": "London"},
        session_id=session_id,
    )
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body or "error" in body


@pytest.mark.payment_on
async def test_mcp_weather_analysis_mcp_with_payment(paid_client) -> None:
    """Priced MCP tool succeeds when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id_with_client(config, client)
    await initialize_mcp_session_with_client(config, client, session_id)
    response = await call_mcp_tool_with_client(
        config,
        client,
        name="get_weather_analysis",
        arguments={"city": "London"},
        session_id=session_id,
    )
    # Parse MCP response and validate against schema
    result_data = parse_mcp_response(response)
    analysis_data = WeatherAnalysisResponse(**result_data)
    assert analysis_data.analysis
    assert "London" in analysis_data.analysis or "weather" in analysis_data.analysis.lower()
