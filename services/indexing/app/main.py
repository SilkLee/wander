"""FastAPI main application for Indexing service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.config import settings
from app.api import health, indexing
from app.services import get_embedding_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.
    
    Startup:
    - Load embedding model
    - Initialize Elasticsearch connection
    
    Shutdown:
    - Cleanup resources
    """
    # Startup
    print(f"Starting Indexing Service on port {settings.port}")
    print(f"Embedding Model: {settings.embedding_model}")
    print(f"Elasticsearch URL: {settings.elasticsearch_url}")
    print(f"Device: {settings.device}")
    
    # Preload embedding model
    print("Preloading embedding model...")
    get_embedding_service()
    print("Embedding model ready")
    
    yield
    
    # Shutdown
    print("Shutting down Indexing Service")


# Create FastAPI app
app = FastAPI(
    title="Indexing Service",
    description="Vector embeddings and hybrid search for WorkflowAI",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(indexing.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "indexing",
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
