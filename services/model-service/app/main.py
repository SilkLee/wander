"""FastAPI main application for Model service."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

from app.config import settings
from app.models.requests import (
    HealthResponse,
    GenerateRequest,
    GenerateResponse,
    ModelInfo,
)
from app.services.inference import get_inference_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    print(f"Starting Model Service on port {settings.port}")
    print(f"Model: {settings.model_name}")
    print(f"Device: {settings.device}")
    
    # Preload model
    print("Loading model...")
    get_inference_service()
    print("Model ready")
    
    yield
    
    # Shutdown
    print("Shutting down Model Service")


# Create FastAPI app
app = FastAPI(
    title="Model Service",
    description="LLM inference service for WorkflowAI",
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "model-service",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    model_loaded = False
    model_name = settings.model_name
    
    try:
        # Use asyncio.to_thread to avoid blocking FastAPI event loop
        inference_service = await asyncio.to_thread(get_inference_service)
        model_loaded = True
    except Exception as e:
        print(f"Model health check failed: {e}")
    
    status_str = "healthy" if model_loaded else "unhealthy"
    
    return HealthResponse(
        status=status_str,
        service="model-service",
        version="0.1.0",
        model_loaded=model_loaded,
        model_name=model_name,
    )


@app.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    try:
        # Use asyncio.to_thread to avoid blocking FastAPI event loop
        await asyncio.to_thread(get_inference_service)
        return {"ready": True}
    except Exception:
        return {"ready": False}


@app.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"alive": True}


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest) -> GenerateResponse:
    """Generate text from prompt."""
    try:
        inference_service = get_inference_service()
        
        # Run synchronous model.generate() in thread pool to avoid blocking event loop
        generated_text, tokens_generated, finish_reason = await asyncio.to_thread(
            inference_service.generate,
            prompt=request.prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop,
        )
        return GenerateResponse(
            text=generated_text,
            prompt=request.prompt,
            tokens_generated=tokens_generated,
            finish_reason=finish_reason,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Generation error: {str(e)}",
        )


@app.post("/generate/stream")
async def generate_stream(request: GenerateRequest):
    """Generate text from prompt with Server-Sent Events streaming."""
    try:
        inference_service = get_inference_service()
        
        async def event_generator():
            """Generate SSE events."""
            try:
                token_count = 0
                for token_text, is_final in inference_service.generate_stream(
                    prompt=request.prompt,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    stop=request.stop,
                ):
                    if is_final:
                        # Send final event with metadata
                        yield f"event: done\n"
                        yield f"data: {{\"tokens_generated\": {token_count}, \"finish_reason\": \"stop\"}}\n\n"
                    else:
                        # Send token event
                        token_count += 1
                        # Escape special characters for JSON
                        escaped_token = token_text.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                        yield f"event: token\n"
                        yield f"data: {{\"token\": \"{escaped_token}\"}}\n\n"
            except Exception as e:
                # Send error event
                yield f"event: error\n"
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming generation error: {str(e)}",
        )


@app.get("/model/info", response_model=ModelInfo)
async def get_model_info() -> ModelInfo:
    """Get model information."""
    try:
        inference_service = get_inference_service()
        info = inference_service.get_model_info()
        
        return ModelInfo(**info)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting model info: {str(e)}",
        )


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
