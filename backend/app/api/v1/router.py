from fastapi import APIRouter
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.dashboard import router as dashboard_router
router = APIRouter()
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(analytics_router)
