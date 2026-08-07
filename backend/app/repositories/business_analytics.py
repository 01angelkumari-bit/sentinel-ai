from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.business.models import Customer, Product, SalesOrder, SalesOrderItem


class BusinessAnalyticsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _revenue() -> Any:
        return SalesOrderItem.quantity * SalesOrderItem.unit_price - SalesOrderItem.discount_amount

    @staticmethod
    def _profit() -> Any:
        return SalesOrderItem.quantity * (SalesOrderItem.unit_price - Product.unit_cost) - SalesOrderItem.discount_amount

    @staticmethod
    def _date_filters(start_date: date | None, end_date: date | None) -> list[Any]:
        filters: list[Any] = [SalesOrder.status != "cancelled"]
        if start_date:
            filters.append(SalesOrder.order_date >= start_date)
        if end_date:
            filters.append(SalesOrder.order_date <= end_date)
        return filters

    def totals(self, start_date: date | None, end_date: date | None) -> dict[str, Any]:
        row = self.db.execute(
            select(
                func.coalesce(func.sum(self._revenue()), 0).label("revenue"),
                func.coalesce(func.sum(self._profit()), 0).label("profit"),
                func.count(func.distinct(SalesOrder.id)).label("order_count"),
                func.count(func.distinct(SalesOrder.customer_id)).label("customer_count"),
            )
            .select_from(SalesOrder)
            .join(SalesOrderItem)
            .join(Product)
            .where(*self._date_filters(start_date, end_date))
        ).mappings().one()
        return dict(row)

    def daily_revenue(self, start_date: date | None, end_date: date | None) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(SalesOrder.order_date.label("date"), func.sum(self._revenue()).label("revenue"))
            .join(SalesOrderItem)
            .where(*self._date_filters(start_date, end_date))
            .group_by(SalesOrder.order_date)
            .order_by(SalesOrder.order_date)
        ).mappings().all()
        return [dict(row) for row in rows]

    def products(self, start_date: date | None, end_date: date | None, limit: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(
                Product.id.label("product_id"), Product.name.label("product"), Product.sku,
                func.sum(SalesOrderItem.quantity).label("units_sold"),
                func.count(func.distinct(SalesOrder.id)).label("orders"),
                func.sum(self._revenue()).label("revenue"), func.sum(self._profit()).label("profit"),
            )
            .select_from(Product).join(SalesOrderItem).join(SalesOrder)
            .where(*self._date_filters(start_date, end_date))
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.sum(self._revenue()).desc()).limit(limit)
        ).mappings().all()
        return [dict(row) for row in rows]

    def regions(self, start_date: date | None, end_date: date | None) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(
                Customer.region, func.count(func.distinct(Customer.id)).label("customers"),
                func.count(func.distinct(SalesOrder.id)).label("orders"),
                func.sum(self._revenue()).label("revenue"), func.sum(self._profit()).label("profit"),
            )
            .select_from(Customer).join(SalesOrder).join(SalesOrderItem).join(Product)
            .where(*self._date_filters(start_date, end_date))
            .group_by(Customer.region).order_by(func.sum(self._revenue()).desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def customer_ltv(self, limit: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(
                Customer.id.label("customer_id"), Customer.company_name.label("customer"), Customer.region,
                func.min(SalesOrder.order_date).label("first_order_date"), func.max(SalesOrder.order_date).label("last_order_date"),
                func.count(func.distinct(SalesOrder.id)).label("orders"), func.sum(self._revenue()).label("lifetime_value"),
            )
            .select_from(Customer).join(SalesOrder).join(SalesOrderItem)
            .where(SalesOrder.status != "cancelled")
            .group_by(Customer.id, Customer.company_name, Customer.region)
            .order_by(func.sum(self._revenue()).desc()).limit(limit)
        ).mappings().all()
        return [dict(row) for row in rows]

