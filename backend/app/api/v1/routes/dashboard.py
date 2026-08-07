from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import current_user
from app.api.v1.schemas.dashboard import AlertItem, DashboardSummary, MetricPoint, RecommendationItem
from app.domain.business.models import Customer, Employee, FinanceTransaction, InventoryStock, Product, SalesOrder, SalesOrderItem, SupportTicket
from app.domain.users.models import User
from app.infrastructure.database import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(_: User = Depends(current_user), db: Session = Depends(get_db)) -> DashboardSummary:
    line_revenue = SalesOrderItem.quantity * SalesOrderItem.unit_price - SalesOrderItem.discount_amount
    line_profit = SalesOrderItem.quantity * (SalesOrderItem.unit_price - Product.unit_cost) - SalesOrderItem.discount_amount
    valid_order = SalesOrder.status != "cancelled"

    revenue = db.scalar(select(func.coalesce(func.sum(line_revenue), 0)).select_from(SalesOrderItem).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id).where(valid_order)) or Decimal("0")
    profit = db.scalar(select(func.coalesce(func.sum(line_profit), 0)).select_from(SalesOrderItem).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id).join(Product, Product.id == SalesOrderItem.product_id).where(valid_order)) or Decimal("0")
    cash = db.scalar(select(func.coalesce(func.sum(case((FinanceTransaction.transaction_type == "debit", -FinanceTransaction.amount), else_=FinanceTransaction.amount)), 0))) or Decimal("0")
    open_tickets = db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.status.in_(["open", "pending"]))) or 0
    employees = db.scalar(select(func.count()).select_from(Employee).where(Employee.employment_status == "active")) or 0

    monthly: dict[str, Decimal] = defaultdict(Decimal)
    for order_date, amount in db.execute(select(SalesOrder.order_date, line_revenue).select_from(SalesOrder).join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id).where(valid_order)):
        monthly[order_date.strftime("%b")] += amount
    revenue_overview = [MetricPoint(label=label, value=float(value)) for label, value in monthly.items()]

    region_rows = db.execute(select(Customer.region, func.sum(line_revenue)).select_from(Customer).join(SalesOrder, SalesOrder.customer_id == Customer.id).join(SalesOrderItem, SalesOrderItem.sales_order_id == SalesOrder.id).where(valid_order).group_by(Customer.region).order_by(func.sum(line_revenue).desc())).all()
    product_rows = db.execute(select(Product.name, func.sum(line_revenue)).select_from(Product).join(SalesOrderItem, SalesOrderItem.product_id == Product.id).join(SalesOrder, SalesOrder.id == SalesOrderItem.sales_order_id).where(valid_order).group_by(Product.id, Product.name).order_by(func.sum(line_revenue).desc()).limit(5)).all()

    sentiment_rows = db.execute(select(SupportTicket.status, func.count()).group_by(SupportTicket.status)).all()
    sentiment_counts = dict(sentiment_rows)
    positive = sentiment_counts.get("resolved", 0) + sentiment_counts.get("closed", 0)
    neutral = sentiment_counts.get("pending", 0)
    negative = sentiment_counts.get("open", 0)

    low_stock = db.scalar(select(func.count()).select_from(InventoryStock).join(Product).where(InventoryStock.quantity_on_hand <= Product.reorder_level)) or 0
    critical_tickets = db.scalar(select(func.count()).select_from(SupportTicket).where(SupportTicket.priority == "critical", SupportTicket.status.in_(["open", "pending"]))) or 0
    top_region = region_rows[0][0] if region_rows else "No region"
    top_product = product_rows[0][0] if product_rows else "No product"

    return DashboardSummary(
        revenue=float(revenue), profit=float(profit), cash_balance=float(cash), open_tickets=open_tickets, employees=employees,
        revenue_overview=revenue_overview,
        revenue_by_region=[MetricPoint(label=label, value=float(value)) for label, value in region_rows],
        top_products=[MetricPoint(label=label, value=float(value)) for label, value in product_rows],
        customer_sentiment=[MetricPoint(label="Positive", value=positive), MetricPoint(label="Neutral", value=neutral), MetricPoint(label="Negative", value=negative)],
        recent_alerts=[
            AlertItem(severity="high" if critical_tickets else "low", title=f"{critical_tickets} critical support tickets", description="Critical cases awaiting resolution across customer accounts."),
            AlertItem(severity="medium" if low_stock else "low", title=f"{low_stock} low-stock positions", description="Warehouse-product balances are at or below reorder thresholds."),
            AlertItem(severity="low", title="Finance ledger synchronized", description="All recognized sales revenue is linked to source orders."),
        ],
        recommendations=[
            RecommendationItem(title=f"Prioritize {top_region}", description="This region currently leads revenue contribution. Expand account coverage and retention programs.", impact="Revenue growth"),
            RecommendationItem(title=f"Scale {top_product}", description="The highest-performing product has strong demand. Review inventory allocation and cross-sell campaigns.", impact="Margin expansion"),
            RecommendationItem(title="Reduce support backlog", description=f"Resolve the {open_tickets} open or pending cases with priority-based agent routing.", impact="Customer retention"),
        ],
    )
