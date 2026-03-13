"""Training API endpoint for the finetune service."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field


class TrainRequest(BaseModel):
    """Request body for POST /train."""

    dataset_path: str = Field(
        ..., min_length=1, description="Path to the training dataset JSONL file"
    )


class TrainResponse(BaseModel):
    """Response body for POST /train."""

    run_id: str = Field(..., description="Unique identifier for this training run")


router = APIRouter()


@router.post("/train", response_model=TrainResponse)
def train(req: TrainRequest) -> TrainResponse:
    """Start a new training run and return its unique run_id."""
    return TrainResponse(run_id=str(uuid4()))
