from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dora import router as dora_router
from app.api.events import router as events_router
from app.config import Settings

settings = Settings()

app = FastAPI(title="Metrics Service", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dora_router)
app.include_router(events_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "metrics"}
