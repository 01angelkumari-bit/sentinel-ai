from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.api.v1.schemas.business_analytics import AnalyticsOverview, BusinessAnalyticsSummary, RankedResponse
from app.application.analytics.service import BusinessAnalyticsService
from app.domain.users.models import User
from app.infrastructure.database import get_db
from app.repositories.business_analytics import BusinessAnalyticsRepository

router = APIRouter(prefix="/analytics", tags=["business analytics"])


def analytics_service(db: Session = Depends(get_db)) -> BusinessAnalyticsService:
    return BusinessAnalyticsService(BusinessAnalyticsRepository(db))


def date_range(
    start_date: date | None = Query(None, description="Inclusive order date in YYYY-MM-DD format"),
    end_date: date | None = Query(None, description="Inclusive order date in YYYY-MM-DD format"),
) -> tuple[date | None, date | None]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_date must be on or before end_date")
    return start_date, end_date


@router.get("/overview", response_model=AnalyticsOverview, summary="Revenue, profit, margin, growth and average order value")
def overview(
    dates: tuple[date | None, date | None] = Depends(date_range),
    _: User = Depends(current_user),
    service: BusinessAnalyticsService = Depends(analytics_service),
) -> dict:
    return service.overview(*dates)


@router.get("/products", response_model=RankedResponse, summary="Top-selling products")
def products(
    dates: tuple[date | None, date | None] = Depends(date_range),
    limit: int = Query(10, ge=1, le=100),
    _: User = Depends(current_user),
    service: BusinessAnalyticsService = Depends(analytics_service),
) -> dict:
    items = service.products(*dates, limit)
    return {"items": items, "count": len(items)}


@router.get("/regions", response_model=RankedResponse, summary="Regional revenue and profitability performance")
def regions(
    dates: tuple[date | None, date | None] = Depends(date_range),
    _: User = Depends(current_user),
    service: BusinessAnalyticsService = Depends(analytics_service),
) -> dict:
    items = service.regions(*dates)
    return {"items": items, "count": len(items)}


@router.get("/customers/lifetime-value", response_model=RankedResponse, summary="Customer lifetime value ranking")
def customer_lifetime_value(
    limit: int = Query(25, ge=1, le=100),
    _: User = Depends(current_user),
    service: BusinessAnalyticsService = Depends(analytics_service),
) -> dict:
    items = service.customer_ltv(limit)
    return {"items": items, "count": len(items)}


@router.get("/summary", response_model=BusinessAnalyticsSummary, summary="Complete executive business analytics payload")
def summary(
    dates: tuple[date | None, date | None] = Depends(date_range),
    product_limit: int = Query(10, ge=1, le=50),
    customer_limit: int = Query(10, ge=1, le=50),
    _: User = Depends(current_user),
    service: BusinessAnalyticsService = Depends(analytics_service),
) -> dict:
    return {
        "overview": service.overview(*dates),
        "top_selling_products": service.products(*dates, product_limit),
        "regional_performance": service.regions(*dates),
        "top_customers_by_ltv": service.customer_ltv(customer_limit),
    }

