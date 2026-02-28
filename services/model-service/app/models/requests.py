"""Request and response models for Model service."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    model_loaded: bool = Field(description="Model loaded status")
    model_name: str = Field(description="Loaded model name")


class GenerateRequest(BaseModel):
    """Text generation request."""

    prompt: str = Field(description="Input prompt")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens to generate")
    temperature: Optional[float] = Field(default=None, description="Sampling temperature")
    top_p: Optional[float] = Field(default=None, description="Nucleus sampling probability")
    stop: Optional[List[str]] = Field(default=None, description="Stop sequences")


class GenerateResponse(BaseModel):
    """Text generation response."""

    text: str = Field(description="Generated text")
    prompt: str = Field(description="Original prompt")
    tokens_generated: int = Field(description="Number of tokens generated")
    finish_reason: str = Field(description="Reason for completion (stop/length)")


class ModelInfo(BaseModel):
    """Model information."""

    name: str = Field(description="Model name/ID")
    type: str = Field(description="Model type (transformers/vllm)")
    device: str = Field(description="Device (cuda/cpu)")
    max_length: int = Field(description="Maximum sequence length")
    parameters: Dict[str, Any] = Field(description="Model parameters")
