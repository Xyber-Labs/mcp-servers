"""Model registry for Together AI image generation models.

This module defines model-specific schemas and capabilities using Pydantic.
"""

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelFamily(str, Enum):
    """Model family identifiers."""
    FLUX_1 = "FLUX.1"
    FLUX_2 = "FLUX.2"
    OTHER = "OTHER"


class ModelCapabilities(BaseModel):
    """Defines what parameters a model supports."""

    supports_negative_prompt: bool = False
    supports_guidance_scale: bool = False
    supports_guidance_param: bool = False  # For FLUX.2-flex which uses "guidance" not "guidance_scale"
    supports_steps: bool = True  # Most models support steps, but FLUX.2-pro doesn't
    supports_lora: bool = False
    requires_disable_safety_checker: bool = False
    response_format: str = "base64"  # "base64" or "b64_json"
    default_response_format: str = "b64_json"  # What Together API expects


class ModelSchema(BaseModel):
    """Schema definition for a specific model."""

    model_name: str = Field(..., description="Full model identifier (e.g., black-forest-labs/FLUX.2-dev)")
    family: ModelFamily = Field(..., description="Model family")
    capabilities: ModelCapabilities = Field(..., description="Model capabilities")

    def build_api_params(self, request_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build API parameters based on model capabilities and request."""
        api_params = {
            "model": self.model_name,
            "prompt": request_params["prompt"],
            "n": 1,
        }

        # Add optional parameters based on model capabilities
        if request_params.get("width") is not None:
            api_params["width"] = request_params["width"]
        if request_params.get("height") is not None:
            api_params["height"] = request_params["height"]
        # Only include steps if the model supports it
        if self.capabilities.supports_steps and request_params.get("steps") is not None:
            api_params["steps"] = request_params["steps"]
        elif request_params.get("steps") is not None and not self.capabilities.supports_steps:
            # Steps was provided but model doesn't support it - will be validated later
            pass
        if request_params.get("seed") is not None and request_params.get("seed") != 0:
            api_params["seed"] = request_params["seed"]

        # Model-specific parameters
        if self.capabilities.requires_disable_safety_checker:
            api_params["disable_safety_checker"] = True

        if self.capabilities.supports_negative_prompt and request_params.get("negative_prompt"):
            api_params["negative_prompt"] = request_params["negative_prompt"]

        if self.capabilities.supports_guidance_param and request_params.get("guidance_scale"):
            # FLUX.2-flex uses "guidance" parameter
            api_params["guidance"] = request_params["guidance_scale"]
        elif self.capabilities.supports_guidance_scale and request_params.get("guidance_scale"):
            # FLUX.1 and older models use "guidance_scale"
            api_params["guidance_scale"] = request_params["guidance_scale"]

        if self.capabilities.supports_lora and request_params.get("lora_scale", 0) > 0:
            api_params["image_loras"] = [
                {
                    "path": request_params.get("lora_url", ""),
                    "scale": float(request_params["lora_scale"]),
                }
            ]

        # Set response format
        api_params["response_format"] = self.capabilities.default_response_format

        # For non-FLUX.2 models, add output_format if dimensions are specified
        if self.family != ModelFamily.FLUX_2 and (
            request_params.get("width") or request_params.get("height")
        ):
            api_params["output_format"] = "png"

        return api_params


# Model Registry - Define all supported models
MODEL_REGISTRY: Dict[str, ModelSchema] = {
    # FLUX.1 models
    "black-forest-labs/FLUX.1-dev": ModelSchema(
        model_name="black-forest-labs/FLUX.1-dev",
        family=ModelFamily.FLUX_1,
        capabilities=ModelCapabilities(
            supports_negative_prompt=True,
            supports_guidance_scale=True,
            supports_lora=False,
            requires_disable_safety_checker=False,
            response_format="base64",
            default_response_format="base64",
        ),
    ),
    "black-forest-labs/FLUX.1-dev-lora": ModelSchema(
        model_name="black-forest-labs/FLUX.1-dev-lora",
        family=ModelFamily.FLUX_1,
        capabilities=ModelCapabilities(
            supports_negative_prompt=True,
            supports_guidance_scale=True,
            supports_lora=True,
            requires_disable_safety_checker=False,
            response_format="base64",
            default_response_format="base64",
        ),
    ),
    # FLUX.2 models
    "black-forest-labs/FLUX.2-pro": ModelSchema(
        model_name="black-forest-labs/FLUX.2-pro",
        family=ModelFamily.FLUX_2,
        capabilities=ModelCapabilities(
            supports_negative_prompt=False,
            supports_guidance_scale=False,
            supports_guidance_param=False,
            supports_steps=False,  # FLUX.2-pro doesn't support steps parameter
            supports_lora=False,
            requires_disable_safety_checker=True,
            response_format="b64_json",
            default_response_format="b64_json",
        ),
    ),
    "black-forest-labs/FLUX.2-dev": ModelSchema(
        model_name="black-forest-labs/FLUX.2-dev",
        family=ModelFamily.FLUX_2,
        capabilities=ModelCapabilities(
            supports_negative_prompt=False,
            supports_guidance_scale=False,
            supports_guidance_param=False,
            supports_lora=False,
            requires_disable_safety_checker=True,
            response_format="b64_json",
            default_response_format="b64_json",
        ),
    ),
    "black-forest-labs/FLUX.2-flex": ModelSchema(
        model_name="black-forest-labs/FLUX.2-flex",
        family=ModelFamily.FLUX_2,
        capabilities=ModelCapabilities(
            supports_negative_prompt=False,
            supports_guidance_scale=False,
            supports_guidance_param=True,  # Uses "guidance" parameter
            supports_lora=False,
            requires_disable_safety_checker=True,
            response_format="b64_json",
            default_response_format="b64_json",
        ),
    ),
}


def get_model_schema(model_name: str) -> ModelSchema:
    """Get model schema from registry.

    Args:
        model_name: Full model identifier (e.g., "black-forest-labs/FLUX.2-dev")

    Returns:
        ModelSchema for the specified model

    Raises:
        ValueError: If model is not found in registry
    """
    if model_name not in MODEL_REGISTRY:
        # Try to infer model family from name
        model_lower = model_name.lower()
        if "flux.2" in model_lower or "flux-2" in model_lower:
            if "flex" in model_lower:
                return MODEL_REGISTRY["black-forest-labs/FLUX.2-flex"]
            elif "pro" in model_lower:
                return MODEL_REGISTRY["black-forest-labs/FLUX.2-pro"]
            else:
                return MODEL_REGISTRY["black-forest-labs/FLUX.2-dev"]
        elif "flux.1" in model_lower or "flux-1" in model_lower:
            if "lora" in model_lower:
                return MODEL_REGISTRY["black-forest-labs/FLUX.1-dev-lora"]
            else:
                return MODEL_REGISTRY["black-forest-labs/FLUX.1-dev"]
        else:
            raise ValueError(
                f"Model '{model_name}' not found in registry. "
                f"Available models: {', '.join(MODEL_REGISTRY.keys())}"
            )
    return MODEL_REGISTRY[model_name]


def list_available_models() -> list[str]:
    """List all available model names in the registry."""
    return list(MODEL_REGISTRY.keys())

