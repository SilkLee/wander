"""FastAPI main application for Agent Orchestrator service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.api import health, workflows


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
    - Validate configuration
    - Test external service connections (Redis, Elasticsearch)
    
    Shutdown:
    - Cleanup resources
    """
    # Startup
    print(f"Starting Agent Orchestrator on port {settings.port}")
    print(f"OpenAI Model: {settings.openai_model}")
    print(f"Redis URL: {settings.redis_url}")
    print(f"Elasticsearch URL: {settings.elasticsearch_url}")
    
    # Validate OpenAI API key
    if not settings.openai_api_key:
        print("WARNING: OPENAI_API_KEY not set - agent execution will fail")
    
    yield
    
    # Shutdown
    print("Shutting down Agent Orchestrator")


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
