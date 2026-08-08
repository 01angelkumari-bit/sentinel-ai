from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_router
from app.core.config import get_settings
app = FastAPI(title="Sentinel AI API", version="1.0.0")
origins = [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Filename", "X-Import-Mode"])
app.include_router(api_router, prefix="/api/v1")
@app.get("/health", tags=["operational"])
def health() -> dict[str, str]: return {"status": "ok"}
