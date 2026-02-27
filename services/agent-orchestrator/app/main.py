"""FastAPI main application for Agent Orchestrator service."""

import asyncio
from contextlib import asynccontextmanager

from redis.asyncio import Redis

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.config import settings
from app.api import health, workflows
from app.consumers import StreamConsumer
from app.workflows import WorkflowProcessor


# Global workflow processor
workflow_processor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
    - Validate configuration
    - Test external service connections (Redis, Elasticsearch)
    - Start workflow processor for stream consumption
    
    Shutdown:
    - Stop workflow processor
    - Cleanup resources
    """
    global workflow_processor
    
    # Startup
    print(f"Starting Agent Orchestrator on port {settings.port}")
    print(f"OpenAI Model: {settings.openai_model}")
    print(f"Redis URL: {settings.redis_url}")
    print(f"Elasticsearch URL: {settings.elasticsearch_url}")
    print(f"Stream Name: {settings.stream_name}")
    
    # Validate OpenAI API key
    if not settings.openai_api_key:
        print("WARNING: OPENAI_API_KEY not set - agent execution will fail")
    
    # Initialize Redis client
    redis_client = Redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=False,  # We'll handle decoding
    )
    
    # Test Redis connection
    try:
        await redis_client.ping()
        print("Connected to Redis successfully")
    except Exception as e:
        print(f"WARNING: Redis connection failed: {e}")
    
    # Create stream consumer
    consumer = StreamConsumer(
        redis_client=redis_client,
        stream_name=settings.stream_name,
        consumer_group=settings.stream_group,
        consumer_name=settings.consumer_name,
        block_ms=5000,
        count=10,
    )
    
    # Create and start workflow processor
    workflow_processor = WorkflowProcessor(consumer)
    await workflow_processor.start()
    print("Workflow processor started")
    
    yield
    
    # Shutdown
    print("Shutting down Agent Orchestrator")
    if workflow_processor:
        await workflow_processor.stop()
    await redis_client.close()
    print("Cleanup complete")

# Create FastAPI app
app = FastAPI(
    title="Agent Orchestrator",
    description="LangChain-based multi-agent workflow orchestration for WorkflowAI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(workflows.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "agent-orchestrator",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


def main():
    """Run the application."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
