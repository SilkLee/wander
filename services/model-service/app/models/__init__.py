"""Model service request/response schemas."""

from .requests import (
    HealthResponse,
    GenerateRequest,
    GenerateResponse,
    ModelInfo,
    RiskClassifyRequest,
    RiskClassifyResponse,
)

__all__ = [
    "HealthResponse",
    "GenerateRequest",
    "GenerateResponse",
    "ModelInfo",
    "RiskClassifyRequest",
    "RiskClassifyResponse",
]
