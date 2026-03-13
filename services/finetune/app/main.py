"""FastAPI main application for the finetune service."""

from fastapi import FastAPI

from app.api.health import router as health_router

app = FastAPI(
    title="Finetune Service",
    description="LoRA fine-tuning service for WorkflowAI",
    version="0.1.0",
)

app.include_router(health_router)
