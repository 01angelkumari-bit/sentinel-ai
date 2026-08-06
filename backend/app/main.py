from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_router
from app.core.config import get_settings
app = FastAPI(title="Sentinel AI API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=get_settings().cors_origins.split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix="/api/v1")
@app.get("/health", tags=["operational"])
def health() -> dict[str, str]: return {"status": "ok"}
