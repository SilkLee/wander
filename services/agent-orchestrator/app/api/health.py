"""Health check endpoint."""

from fastapi import APIRouter, HTTPException
from redis import asyncio as aioredis
from elasticsearch import AsyncElasticsearch

from app.config import settings
from app.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns service status and external service connectivity.
    """
    redis_connected = False
    elasticsearch_connected = False

    # Check Redis connection
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await redis_client.ping()
        redis_connected = True
        await redis_client.aclose()
    except Exception as e:
        print(f"Redis connection failed: {e}")

    # Check Elasticsearch connection
    try:
        es_client = AsyncElasticsearch([settings.elasticsearch_url])
        await es_client.info()
        elasticsearch_connected = True
        await es_client.close()
    except Exception as e:
        print(f"Elasticsearch connection failed: {e}")

    return HealthResponse(
        status="healthy",
        service="agent-orchestrator",
        version="0.1.0",
        redis_connected=redis_connected,
        elasticsearch_connected=elasticsearch_connected,
    )


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/Docker health probes.

    Returns 200 if service is ready to accept traffic.
    """
    # Check critical dependencies
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.aclose()
    except Exception:
        raise HTTPException(status_code=503, detail="Redis not available")

    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes/Docker health probes.

    Returns 200 if service process is alive.
    """
    return {"status": "alive"}
