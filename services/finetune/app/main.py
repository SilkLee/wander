"""FastAPI main application for the finetune service."""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.train import router as train_router

app = FastAPI(
    title="Finetune Service",
    description="LoRA fine-tuning service for WorkflowAI",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(train_router)
