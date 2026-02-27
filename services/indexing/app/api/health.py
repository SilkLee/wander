"""Health check endpoints for Indexing service."""

from fastapi import APIRouter

from app.models.requests import HealthResponse
from app.services import get_embedding_service, get_search_service
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check.
    
    Checks:
    - Service availability
    - Elasticsearch connection
    - Embedding model loaded
    
    Returns:
        Health status with component checks
    """
    # Check Elasticsearch
    search_service = await get_search_service()
    es_connected = False
    try:
        await search_service.es.ping()
        es_connected = True
    except Exception as e:
        print(f"Elasticsearch health check failed: {e}")

    # Check embedding model
    model_loaded = False
    try:
        embedding_service = get_embedding_service()
        model_loaded = True
    except Exception as e:
        print(f"Embedding model health check failed: {e}")

    status = "healthy" if (es_connected and model_loaded) else "degraded"

    return HealthResponse(
        status=status,
        service="indexing",
        version="0.1.0",
        elasticsearch_connected=es_connected,
        model_loaded=model_loaded,
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe.
    
    Returns 200 if service is ready to accept traffic.
    """
    # Check critical components
    search_service = await get_search_service()
    try:
        await search_service.es.ping()
        get_embedding_service()
        return {"ready": True}
    except Exception:
        return {"ready": False}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe.
    
    Returns 200 if service is alive (basic check).
    """
    return {"alive": True}
