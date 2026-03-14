from fastapi import FastAPI
from app.api.dora import router as dora_router

app = FastAPI(title="Metrics Service", version="0.1.0")
app.include_router(dora_router)
