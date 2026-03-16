"""Evaluation API endpoint for the finetune service."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """Request body for POST /evaluate."""

    run_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier of the training run to evaluate",
    )


class EvaluateMetrics(BaseModel):
    """Evaluation metrics returned by POST /evaluate."""

    macro_f1: float = Field(..., description="Macro-averaged F1 score")
    high_risk_recall: float = Field(..., description="Recall for the high-risk class")


class EvaluateResponse(BaseModel):
    """Response body for POST /evaluate."""

    metrics: EvaluateMetrics = Field(..., description="Evaluation metrics for the run")


router = APIRouter()


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(req: EvaluateRequest) -> EvaluateResponse:
    """Evaluate a training run and return metrics."""
    return EvaluateResponse(metrics=EvaluateMetrics(macro_f1=0.0, high_risk_recall=0.0))
