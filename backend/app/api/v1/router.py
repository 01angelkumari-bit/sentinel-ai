from fastapi import APIRouter
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.analytics import router as analytics_router
from app.api.v1.routes.business_analytics import router as business_analytics_router
from app.api.v1.routes.files import router as files_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.datasets import router as datasets_router
from app.api.v1.routes.ai import router as ai_router
from app.api.v1.routes.governance import router as governance_router
router = APIRouter()
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(analytics_router)
router.include_router(business_analytics_router)
router.include_router(files_router)
router.include_router(datasets_router)
router.include_router(ai_router)
router.include_router(governance_router)
