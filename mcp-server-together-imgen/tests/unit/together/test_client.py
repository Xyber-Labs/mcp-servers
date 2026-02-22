from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server_together_imgen.together.client import TogetherClient
from mcp_server_together_imgen.together.config import TogetherSettings
from tests.unit.together.mocks import (
    MockHTTPResponse,
    MockTogetherHttpClient,
    build_chat_completion_response,
    build_image_response,
    build_image_response_with_base64,
    build_image_response_with_url,
)


@pytest.fixture
def together_settings() -> TogetherSettings:
    """Provide TogetherSettings with test configuration."""
    # Pass _env_file=None to skip loading .env file which may have extra fields
    return TogetherSettings(
        api_key="test-api-key",
        default_model="black-forest-labs/FLUX.1-dev",
        lora_model="black-forest-labs/FLUX.1-dev-lora",
        refiner_model="deepseek-ai/DeepSeek-V3",
        generation_timeout=30,
        _env_file=None,
    )


@pytest.fixture
def together_client(together_settings: TogetherSettings) -> TogetherClient:
    """Provide a TogetherClient with test configuration."""
    return TogetherClient(together_settings)


def _patch_httpx_client(mock_client: MockTogetherHttpClient):
    """Create a context manager that patches httpx.AsyncClient."""
    return patch("httpx.AsyncClient", return_value=mock_client)


# =============================================================================
# Feature 1: Generate Image
# =============================================================================


class TestGenerateImage:
    """Tests for generate_image method."""

    async def test_generate_image_success(self, together_client: TogetherClient):
        """Successful image generation returns base64 string."""
        b64_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAA"
        payload = build_image_response(b64_json=b64_data)
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.generate_image("a cat in space")

        assert isinstance(result, str)
        assert result == b64_data
        assert len(mock_client.calls) == 1
        assert mock_client.calls[0]["json"]["prompt"] == "a cat in space"

    async def test_generate_image_uses_default_model(
        self, together_client: TogetherClient
    ):
        """Image generation uses default model when not specified."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image("test prompt")

        assert mock_client.calls[0]["json"]["model"] == "black-forest-labs/FLUX.1-dev"

    async def test_generate_image_with_custom_model(
        self, together_client: TogetherClient
    ):
        """Image generation uses custom model when specified."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image(
                "test prompt", model="custom-model/v1"
            )

        assert mock_client.calls[0]["json"]["model"] == "custom-model/v1"

    async def test_generate_image_with_dimensions(
        self, together_client: TogetherClient
    ):
        """Image generation respects width and height parameters."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image(
                "test prompt", width=512, height=768
            )

        assert mock_client.calls[0]["json"]["width"] == 512
        assert mock_client.calls[0]["json"]["height"] == 768

    async def test_generate_image_with_optional_params(
        self, together_client: TogetherClient
    ):
        """Image generation includes optional parameters when provided."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image(
                "test prompt",
                steps=30,
                guidance_scale=7.5,
                negative_prompt="blurry",
                seed=12345,
            )

        api_params = mock_client.calls[0]["json"]
        assert api_params["steps"] == 30
        assert api_params["guidance_scale"] == 7.5
        assert api_params["negative_prompt"] == "blurry"
        assert api_params["seed"] == 12345

    async def test_generate_image_skips_zero_seed(
        self, together_client: TogetherClient
    ):
        """Seed of 0 is not included in API parameters."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image("test prompt", seed=0)

        api_params = mock_client.calls[0]["json"]
        assert "seed" not in api_params

    async def test_generate_image_handles_base64_format(
        self, together_client: TogetherClient
    ):
        """Image generation handles 'base64' key in response."""
        b64_data = "base64DataHere"
        payload = build_image_response_with_base64(base64=b64_data)
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.generate_image("test prompt")

        assert result == b64_data

    async def test_generate_image_strips_newlines(
        self, together_client: TogetherClient
    ):
        """Newlines in base64 response are stripped."""
        b64_data = "base64\nwith\nnewlines"
        payload = build_image_response(b64_json=b64_data)
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.generate_image("test prompt")

        assert "\n" not in result
        assert result == "base64withnewlines"

    async def test_generate_image_sends_auth_header(
        self, together_client: TogetherClient
    ):
        """API key is sent in Authorization header."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image("test prompt")

        assert mock_client.calls[0]["headers"]["Authorization"] == "Bearer test-api-key"


# =============================================================================
# Feature 2: Generate Image with LoRA
# =============================================================================


class TestGenerateImageWithLora:
    """Tests for generate_image_with_lora method."""

    async def test_generate_image_with_lora_success(
        self, together_client: TogetherClient
    ):
        """Successful LoRA image generation returns base64 string."""
        b64_data = "loraImageBase64"
        payload = build_image_response(b64_json=b64_data)
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.generate_image_with_lora(
                "a portrait", lora_url="https://example.com/lora.safetensors"
            )

        assert result == b64_data
        api_params = mock_client.calls[0]["json"]
        assert "image_loras" in api_params
        assert api_params["image_loras"][0]["path"] == "https://example.com/lora.safetensors"

    async def test_generate_image_with_lora_uses_lora_model(
        self, together_client: TogetherClient
    ):
        """LoRA generation uses lora_model by default."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image_with_lora(
                "test prompt", lora_url="https://example.com/lora.safetensors"
            )

        assert mock_client.calls[0]["json"]["model"] == "black-forest-labs/FLUX.1-dev-lora"

    async def test_generate_image_with_lora_custom_scale(
        self, together_client: TogetherClient
    ):
        """LoRA scale parameter is correctly set."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image_with_lora(
                "test prompt",
                lora_url="https://example.com/lora.safetensors",
                lora_scale=0.75,
            )

        api_params = mock_client.calls[0]["json"]
        assert api_params["image_loras"][0]["scale"] == 0.75

    async def test_generate_image_with_lora_optional_params(
        self, together_client: TogetherClient
    ):
        """LoRA generation includes optional parameters."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image_with_lora(
                "test prompt",
                lora_url="https://example.com/lora.safetensors",
                steps=25,
                guidance_scale=5.0,
                seed=42,
            )

        api_params = mock_client.calls[0]["json"]
        assert api_params["steps"] == 25
        assert api_params["guidance_scale"] == 5.0
        assert api_params["seed"] == 42


# =============================================================================
# Feature 3: Refine Prompt
# =============================================================================


class TestRefinePrompt:
    """Tests for refine_prompt method."""

    async def test_refine_prompt_success(self, together_client: TogetherClient):
        """Successful prompt refinement returns refined text."""
        refined_text = "A majestic feline floating in the cosmic void"
        payload = build_chat_completion_response(content=refined_text)
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.refine_prompt("a cat in space")

        assert result == refined_text

    async def test_refine_prompt_standard_mode(
        self, together_client: TogetherClient
    ):
        """Standard mode uses standard refinement instruction."""
        payload = build_chat_completion_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.refine_prompt("test prompt", mode="standard")

        messages = mock_client.calls[0]["json"]["messages"]
        user_message = messages[1]["content"]
        assert "FLUX image generation" in user_message

    async def test_refine_prompt_lora_mode(self, together_client: TogetherClient):
        """LoRA mode uses LoRA-specific refinement instruction."""
        payload = build_chat_completion_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.refine_prompt("test prompt", mode="lora")

        messages = mock_client.calls[0]["json"]["messages"]
        user_message = messages[1]["content"]
        assert "LoRA adapter" in user_message or "fine-tuned" in user_message

    async def test_refine_prompt_uses_refiner_model(
        self, together_client: TogetherClient
    ):
        """Prompt refinement uses configured refiner model."""
        payload = build_chat_completion_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.refine_prompt("test prompt")

        assert mock_client.calls[0]["json"]["model"] == "deepseek-ai/DeepSeek-V3"

    async def test_refine_prompt_calls_chat_api(self, together_client: TogetherClient):
        """Prompt refinement calls the chat completions endpoint."""
        payload = build_chat_completion_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.refine_prompt("test prompt")

        assert "chat/completions" in mock_client.calls[0]["url"]

    async def test_refine_prompt_fallback_on_error(
        self, together_client: TogetherClient
    ):
        """On error, returns original prompt."""
        mock_client = MockTogetherHttpClient(
            [MockHTTPResponse(payload={}, status_code=500)]
        )

        with _patch_httpx_client(mock_client):
            result = await together_client.refine_prompt("original prompt")

        assert result == "original prompt"

    async def test_refine_prompt_fallback_on_empty_response(
        self, together_client: TogetherClient
    ):
        """Returns original prompt if refined content is empty."""
        payload = build_chat_completion_response(content="")
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            result = await together_client.refine_prompt("original prompt")

        assert result == "original prompt"


# =============================================================================
# Feature 4: Error Handling
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in TogetherClient."""

    async def test_empty_api_key_raises_value_error(
        self, together_settings: TogetherSettings
    ):
        """Empty API key raises ValueError."""
        together_settings.api_key = ""
        client = TogetherClient(together_settings)

        with pytest.raises(ValueError, match="TOGETHER_API_KEY is not set"):
            await client.generate_image("test prompt")

    async def test_whitespace_api_key_raises_value_error(
        self, together_settings: TogetherSettings
    ):
        """Whitespace-only API key raises ValueError."""
        together_settings.api_key = "   "
        client = TogetherClient(together_settings)

        with pytest.raises(ValueError, match="TOGETHER_API_KEY is not set"):
            await client.generate_image("test prompt")

    async def test_unauthorized_error_message(self, together_client: TogetherClient):
        """401 error provides helpful message about API key."""
        mock_client = MockTogetherHttpClient(
            [MockHTTPResponse(payload={}, status_code=401)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(Exception, match="Invalid API key"):
                await together_client.generate_image("test prompt")

    async def test_rate_limit_error_message(self, together_client: TogetherClient):
        """429 error provides rate limit message."""
        mock_client = MockTogetherHttpClient(
            [MockHTTPResponse(payload={}, status_code=429)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(Exception, match="Rate limit"):
                await together_client.generate_image("test prompt")

    async def test_not_found_error_message(self, together_client: TogetherClient):
        """404 error provides model not found message."""
        mock_client = MockTogetherHttpClient(
            [MockHTTPResponse(payload={}, status_code=404)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(Exception, match="not found"):
                await together_client.generate_image("test prompt")

    async def test_server_error_propagates(self, together_client: TogetherClient):
        """500 error is propagated."""
        mock_client = MockTogetherHttpClient(
            [MockHTTPResponse(payload={}, status_code=500)]
        )

        with _patch_httpx_client(mock_client):
            with pytest.raises(Exception):
                await together_client.generate_image("test prompt")

    async def test_invalid_response_structure_raises_error(
        self, together_client: TogetherClient
    ):
        """Invalid response structure raises ValueError."""
        payload = {"error": "something went wrong"}  # missing 'data' key
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            with pytest.raises(ValueError, match="Invalid response structure"):
                await together_client.generate_image("test prompt")

    async def test_empty_data_array_raises_error(
        self, together_client: TogetherClient
    ):
        """Empty data array raises ValueError."""
        payload = {"data": []}
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            with pytest.raises(ValueError, match="No image data"):
                await together_client.generate_image("test prompt")

    async def test_url_response_raises_error(self, together_client: TogetherClient):
        """URL in response instead of base64 raises ValueError."""
        payload = build_image_response_with_url()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            with pytest.raises(ValueError, match="URL instead of base64"):
                await together_client.generate_image("test prompt")

    async def test_missing_base64_data_raises_error(
        self, together_client: TogetherClient
    ):
        """Missing base64 data raises ValueError."""
        payload = {"data": [{"index": 0}]}  # no b64_json or base64
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            with pytest.raises(ValueError, match="Empty or missing base64"):
                await together_client.generate_image("test prompt")


# =============================================================================
# Feature 5: API Endpoint URLs
# =============================================================================


class TestApiEndpoints:
    """Tests for correct API endpoint usage."""

    async def test_image_generation_endpoint(self, together_client: TogetherClient):
        """Image generation calls the images/generations endpoint."""
        payload = build_image_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.generate_image("test prompt")

        assert mock_client.calls[0]["url"] == "https://api.together.xyz/v1/images/generations"

    async def test_chat_completion_endpoint(self, together_client: TogetherClient):
        """Prompt refinement calls the chat/completions endpoint."""
        payload = build_chat_completion_response()
        mock_client = MockTogetherHttpClient([MockHTTPResponse(payload=payload)])

        with _patch_httpx_client(mock_client):
            await together_client.refine_prompt("test prompt")

        assert mock_client.calls[0]["url"] == "https://api.together.xyz/v1/chat/completions"
