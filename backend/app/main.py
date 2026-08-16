import logging
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.infrastructure.database import get_db
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi import Depends
app = FastAPI(title="Sentinel AI API", version="1.0.0")
origins = [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Filename", "X-Import-Mode"])
app.include_router(api_router, prefix="/api/v1")

performance_logger = logging.getLogger("sentinel.performance")


@app.middleware("http")
async def request_performance(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    started = perf_counter()
    is_auth = request.url.path.startswith("/api/v1/auth")
    if is_auth:
        performance_logger.info("AUTH_REQUEST_START request_id=%s path=%s", request_id, request.url.path)
    response = await call_next(request)
    total_ms = (perf_counter() - started) * 1000
    existing = response.headers.get("Server-Timing")
    response.headers["Server-Timing"] = f"{existing}, total;dur={total_ms:.1f}" if existing else f"total;dur={total_ms:.1f}"
    response.headers["X-Request-ID"] = request_id
    if is_auth:
        performance_logger.info("AUTH_REQUEST_END request_id=%s path=%s status=%s total_ms=%.2f", request_id, request.url.path, response.status_code, total_ms)
    return response

@app.get("/health", tags=["operational"])
def health() -> dict[str, str]: return {"status": "ok"}
@app.get("/ready", tags=["operational"])
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is unavailable") from exc
    return {"status": "ready", "database": "ok"}
