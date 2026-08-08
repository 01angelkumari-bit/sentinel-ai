from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.api.v1.schemas.analytics import AnalyticsResponse
from app.domain.users.models import User
from app.infrastructure.database import get_db
from app.repositories.analytics import AnalyticsRepository

router = APIRouter(tags=["business intelligence"])


def repository(user: User = Depends(current_user), db: Session = Depends(get_db)) -> AnalyticsRepository:
    return AnalyticsRepository(db, user.organization_id)


def pagination(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100)) -> tuple[int, int]:
    return page, page_size


@router.get("/sales", response_model=AnalyticsResponse, summary="List sales orders and revenue trend")
def sales(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("order_date", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "desc",
    status: str | None = Query(None, min_length=1, max_length=20),
    customer: str | None = Query(None, min_length=2, max_length=200),
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.sales(*paging, sort_by, sort_order, status, customer)


@router.get("/finance", response_model=AnalyticsResponse, summary="List finance transactions and account balances")
def finance(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("transaction_date", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "desc",
    transaction_type: str | None = Query(None, min_length=1, max_length=20),
    account_type: str | None = Query(None, min_length=1, max_length=30),
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.finance(*paging, sort_by, sort_order, transaction_type, account_type)


@router.get("/inventory", response_model=AnalyticsResponse, summary="List warehouse inventory and availability")
def inventory(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("available", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "asc",
    warehouse: str | None = Query(None, min_length=1, max_length=20),
    low_stock: bool | None = None,
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.inventory(*paging, sort_by, sort_order, warehouse, low_stock)


@router.get("/support", response_model=AnalyticsResponse, summary="List support tickets and status distribution")
def support(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("opened_at", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "desc",
    status: str | None = Query(None, min_length=1, max_length=20),
    priority: str | None = Query(None, min_length=1, max_length=20),
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.support(*paging, sort_by, sort_order, status, priority)


@router.get("/employees", response_model=AnalyticsResponse, summary="List employees and department distribution")
def employees(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("employee_number", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "asc",
    department: str | None = Query(None, min_length=1, max_length=20),
    employment_status: str | None = Query(None, min_length=1, max_length=20),
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.employees(*paging, sort_by, sort_order, department, employment_status)


@router.get("/customers", response_model=AnalyticsResponse, summary="List customers and regional distribution")
def customers(
    paging: tuple[int, int] = Depends(pagination),
    sort_by: str = Query("company_name", min_length=1, max_length=40),
    sort_order: Literal["asc", "desc"] = "asc",
    region: str | None = Query(None, min_length=1, max_length=80),
    status: str | None = Query(None, min_length=1, max_length=20),
    search: str | None = Query(None, min_length=2, max_length=200),
    _: User = Depends(current_user),
    repo: AnalyticsRepository = Depends(repository),
) -> dict:
    return repo.customers(*paging, sort_by, sort_order, region, status, search)
