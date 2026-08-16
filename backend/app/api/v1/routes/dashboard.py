import calendar
from decimal import Decimal
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.api.v1.schemas.dashboard import AlertItem, DashboardSummary, MetricPoint, RecommendationItem
from app.application.ai.dataset_analysis import analyze_business_risks, analyze_sentiment
from app.application.ai.dataset_context import TenantDatasetContext
from app.domain.business.models import Customer, Employee, FinanceTransaction, InventoryStock, Product, SalesOrder, SalesOrderItem, SupportTicket
from app.domain.users.models import DatasetImport, User
from app.infrastructure.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
SUMMARY_CACHE: dict[tuple[str, str], tuple[float, DashboardSummary]] = {}
SUMMARY_CACHE_LOCK = Lock()
SUMMARY_CACHE_TTL_SECONDS = 30


@router.get("/summary", response_model=DashboardSummary)
def summary(user: User = Depends(current_user), db: Session = Depends(get_db)) -> DashboardSummary:
    version = db.scalar(select(func.max(DatasetImport.completed_at)).where(DatasetImport.organization_id == user.organization_id))
    cache_key = (str(user.organization_id), version.isoformat() if version else "none")
    with SUMMARY_CACHE_LOCK:
        cached = SUMMARY_CACHE.get(cache_key)
        if cached and cached[0] > monotonic():
            return cached[1]
    line_revenue = SalesOrderItem.quantity * SalesOrderItem.unit_price - SalesOrderItem.discount_amount
    line_profit = SalesOrderItem.quantity * (SalesOrderItem.unit_price - Product.unit_cost) - SalesOrderItem.discount_amount
    valid_order = (SalesOrder.status != "cancelled") & (SalesOrder.organization_id == user.organization_id)

    revenue, profit = db.execute(select(func.coalesce(func.sum(line_revenue), 0), func.coalesce(func.sum(line_profit), 0)).select_from(SalesOrderItem).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id).join(Product, Product.id == SalesOrderItem.product_id).where(valid_order)).one()
    cash = db.scalar(select(func.coalesce(func.sum(case((FinanceTransaction.transaction_type == "debit", -FinanceTransaction.amount), else_=FinanceTransaction.amount)), 0)).where(FinanceTransaction.organization_id == user.organization_id)) or Decimal("0")
    open_tickets = db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.organization_id == user.organization_id, SupportTicket.status.in_(["open", "pending"]))) or 0
    employees = db.scalar(select(func.count()).select_from(Employee).where(Employee.organization_id == user.organization_id, Employee.employment_status == "active")) or 0

    year = func.extract("year", SalesOrder.order_date)
    month = func.extract("month", SalesOrder.order_date)
    monthly_rows = db.execute(
        select(year, month, func.sum(line_revenue))
        .select_from(SalesOrder)
        .join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id)
        .where(valid_order)
        .group_by(year, month)
        .order_by(year, month)
    ).all()
    revenue_overview = [MetricPoint(label=f"{calendar.month_abbr[int(month_value)]} {int(year_value)}", value=float(value)) for year_value, month_value, value in monthly_rows]

    region_rows = db.execute(select(Customer.region, func.sum(line_revenue)).select_from(Customer).join(SalesOrder, SalesOrder.customer_id == Customer.id).join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id).where(valid_order).group_by(Customer.region).order_by(func.sum(line_revenue).desc())).all()
    product_rows = db.execute(select(Product.name, func.sum(line_revenue)).select_from(Product).join(SalesOrderItem, SalesOrderItem.product_id == Product.id).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id).where(valid_order).group_by(Product.id, Product.name).order_by(func.sum(line_revenue).desc()).limit(5)).all()

    context = TenantDatasetContext(db, user.organization_id)
    active_frame = context.load_active()
    sentiment = analyze_sentiment(active_frame)
    risks = analyze_business_risks(active_frame)

    result = DashboardSummary(
        revenue=float(revenue), profit=float(profit), cash_balance=float(cash), open_tickets=open_tickets, employees=employees,
        revenue_overview=revenue_overview,
        revenue_by_region=[MetricPoint(label=label, value=float(value)) for label, value in region_rows],
        top_products=[MetricPoint(label=label, value=float(value)) for label, value in product_rows],
        customer_sentiment=[MetricPoint(**item) for item in sentiment["distribution"]],
        sentiment_available=bool(sentiment["available"]), sentiment_score=sentiment.get("score"), sentiment_label=sentiment.get("label"), sentiment_message=sentiment["message"],
        recent_alerts=[AlertItem(severity=item["severity"], title=item["category"], description=item["evidence"], confidence=95) for item in risks[:4]],
        recommendations=[RecommendationItem(title=f"Address {item['category']}", description=item["recommendation"], impact=item["metric"], priority=item["severity"]) for item in risks[:4]],
        source_counts={
            "sales": db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.organization_id == user.organization_id)) or 0,
            "finance": db.scalar(select(func.count()).select_from(FinanceTransaction).where(FinanceTransaction.organization_id == user.organization_id)) or 0,
            "inventory": db.scalar(select(func.count()).select_from(InventoryStock).where(InventoryStock.organization_id == user.organization_id)) or 0,
            "support": db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.organization_id == user.organization_id)) or 0,
            "employees": db.scalar(select(func.count()).select_from(Employee).where(Employee.organization_id == user.organization_id)) or 0,
            "customers": db.scalar(select(func.count()).select_from(Customer).where(Customer.organization_id == user.organization_id)) or 0,
        },
    )
    with SUMMARY_CACHE_LOCK:
        SUMMARY_CACHE[cache_key] = (monotonic() + SUMMARY_CACHE_TTL_SECONDS, result)
        stale = [key for key, (expires, _) in SUMMARY_CACHE.items() if expires <= monotonic() or key[0] == str(user.organization_id) and key != cache_key]
        for key in stale:
            SUMMARY_CACHE.pop(key, None)
    return result
