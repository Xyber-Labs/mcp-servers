from __future__ import annotations

import pytest

from mcp_server_together_imgen.schemas import ImageResponse
from tests.e2e.config import load_e2e_config, require_base_url
from tests.e2e.utils import (
    call_mcp_tool,
    initialize_mcp_session,
    negotiate_mcp_session_id,
    parse_mcp_response,
)

# Simple prompt to minimize API costs
TEST_PROMPT = "A red square"

# =============================================================================
# /hybrid/pricing - Free endpoint
# =============================================================================


async def test_hybrid_pricing_rest(rest_client) -> None:
    """Smoke test: /hybrid/pricing via REST (always free)."""
    config, client = rest_client
    response = await client.get("/hybrid/pricing")
    assert response.status_code == 200
    data = response.json()
    assert "pricing" in data
    assert isinstance(data["pricing"], dict)


async def test_hybrid_pricing_mcp() -> None:
    """Smoke test: pricing info via MCP (always free)."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="together_imgen_get_pricing",
        arguments={},
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    assert "pricing" in data
    assert isinstance(data["pricing"], dict)


# =============================================================================
# /hybrid/generate - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_hybrid_generate_rest_pricing_off(rest_client) -> None:
    """Priced endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    params = {
        "prompt": TEST_PROMPT,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate", params=params)
    assert response.status_code == 200
    # Validate response against schema
    image_data = ImageResponse(**response.json())
    assert image_data.image_base64
    assert image_data.model_used
    print(f"\nGenerated image with model: {image_data.model_used}")


@pytest.mark.payment_on
async def test_hybrid_generate_rest_no_payment(rest_client) -> None:
    """Priced endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    params = {
        "prompt": TEST_PROMPT,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate", params=params)
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.payment_on
async def test_hybrid_generate_rest_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    params = {
        "prompt": TEST_PROMPT,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate", params=params)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    image_data = ImageResponse(**response.json())
    assert image_data.image_base64
    assert image_data.model_used
    print(f"\nGenerated image with model: {image_data.model_used}")


@pytest.mark.payment_off
async def test_hybrid_generate_mcp_pricing_off() -> None:
    """Priced endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="generate_image",
        arguments={
            "prompt": TEST_PROMPT,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    image_data = ImageResponse(**data)
    assert image_data.image_base64
    assert image_data.model_used
    print(f"\nGenerated image with model: {image_data.model_used}")


@pytest.mark.payment_on
async def test_hybrid_generate_mcp_no_payment() -> None:
    """Priced endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="generate_image",
        arguments={
            "prompt": TEST_PROMPT,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_hybrid_generate_mcp_with_payment(paid_client) -> None:
    """Priced endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="generate_image",
        arguments={
            "prompt": TEST_PROMPT,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
        client=client,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    image_data = ImageResponse(**data)
    assert image_data.image_base64
    assert image_data.model_used
    print(f"\nGenerated image with model: {image_data.model_used}")


# =============================================================================
# /hybrid/generate-lora - Priced endpoint
# =============================================================================


@pytest.mark.payment_off
async def test_hybrid_generate_lora_rest_pricing_off(rest_client) -> None:
    """Priced LoRA endpoint works via REST without payment when PRICING_MODE=off."""
    config, client = rest_client
    params = {
        "prompt": TEST_PROMPT,
        "lora_scale": 0.8,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate-lora", params=params)
    assert response.status_code == 200
    # Validate response against schema
    image_data = ImageResponse(**response.json())
    assert image_data.image_base64
    assert image_data.model_used
    assert image_data.lora_url  # Uses default from LORA_URL env var
    print(f"\nGenerated LoRA image with model: {image_data.model_used}")


@pytest.mark.payment_on
async def test_hybrid_generate_lora_rest_no_payment(rest_client) -> None:
    """Priced LoRA endpoint returns 402 via REST when PRICING_MODE=on and no payment."""
    config, client = rest_client
    params = {
        "prompt": TEST_PROMPT,
        "lora_scale": 0.8,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate-lora", params=params)
    assert response.status_code == 402
    body = response.json()
    assert "accepts" in body and body["accepts"]
    assert body.get("error")


@pytest.mark.payment_on
async def test_hybrid_generate_lora_rest_with_payment(paid_client) -> None:
    """Priced LoRA endpoint succeeds via REST when PRICING_MODE=on and payment provided."""
    config, client = paid_client
    params = {
        "prompt": TEST_PROMPT,
        "lora_scale": 0.8,
        "width": 256,
        "height": 256,
        "steps": 4,
    }
    response = await client.post("/hybrid/generate-lora", params=params)
    if response.status_code == 402:
        error_body = response.json()
        pytest.fail(
            f"Payment-enabled test received 402 response. "
            f"Payment flow may not be working correctly. "
            f"Error body: {error_body}"
        )
    response.raise_for_status()
    # Validate response against schema
    image_data = ImageResponse(**response.json())
    assert image_data.image_base64
    assert image_data.model_used
    assert image_data.lora_url  # Uses default from LORA_URL env var
    print(f"\nGenerated LoRA image with model: {image_data.model_used}")


@pytest.mark.payment_off
async def test_hybrid_generate_lora_mcp_pricing_off() -> None:
    """Priced LoRA endpoint works via MCP without payment when PRICING_MODE=off."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="generate_image_with_lora",
        arguments={
            "prompt": TEST_PROMPT,
            "lora_scale": 0.8,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    image_data = ImageResponse(**data)
    assert image_data.image_base64
    assert image_data.model_used
    assert image_data.lora_url  # Uses default from LORA_URL env var
    print(f"\nGenerated LoRA image with model: {image_data.model_used}")


@pytest.mark.payment_on
async def test_hybrid_generate_lora_mcp_no_payment() -> None:
    """Priced LoRA endpoint returns 402 via MCP when PRICING_MODE=on and no payment."""
    config = load_e2e_config()
    require_base_url(config)

    session_id = await negotiate_mcp_session_id(config)
    await initialize_mcp_session(config, session_id)
    response = await call_mcp_tool(
        config,
        name="generate_image_with_lora",
        arguments={
            "prompt": TEST_PROMPT,
            "lora_scale": 0.8,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
    )
    assert response.status_code == 402


@pytest.mark.payment_on
async def test_hybrid_generate_lora_mcp_with_payment(paid_client) -> None:
    """Priced LoRA endpoint succeeds via MCP when PRICING_MODE=on and payment provided."""
    config, client = paid_client

    session_id = await negotiate_mcp_session_id(config, client)
    await initialize_mcp_session(config, session_id, client)
    response = await call_mcp_tool(
        config,
        name="generate_image_with_lora",
        arguments={
            "prompt": TEST_PROMPT,
            "lora_scale": 0.8,
            "width": 256,
            "height": 256,
            "steps": 4,
        },
        session_id=session_id,
        client=client,
    )

    is_error, data = parse_mcp_response(response)
    assert not is_error
    image_data = ImageResponse(**data)
    assert image_data.image_base64
    assert image_data.model_used
    assert image_data.lora_url  # Uses default from LORA_URL env var
    print(f"\nGenerated LoRA image with model: {image_data.model_used}")
