from __future__ import annotations

from math import ceil
from typing import Any

from fastapi import HTTPException, status
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.domain.business.models import (
    Customer,
    Department,
    Employee,
    FinanceAccount,
    FinanceTransaction,
    InventoryStock,
    Product,
    SalesOrder,
    SalesOrderItem,
    SupportTicket,
    Warehouse,
)


class AnalyticsRepository:
    """Read-only BI repository with bounded pagination and safe sorting."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _paginate(
        self,
        statement: Select[Any],
        count_statement: Select[Any],
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        sortable: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        column = sortable.get(sort_by)
        if column is None:
            allowed = ", ".join(sorted(sortable))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid sort_by '{sort_by}'. Allowed values: {allowed}",
            )
        ordering = column.desc() if sort_order == "desc" else column.asc()
        total = int(self.db.scalar(count_statement) or 0)
        rows = self.db.execute(statement.order_by(ordering).offset((page - 1) * page_size).limit(page_size)).mappings().all()
        return [dict(row) for row in rows], {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": ceil(total / page_size) if total else 0,
        }

    def sales(self, page: int, page_size: int, sort_by: str, sort_order: str, status_filter: str | None, customer: str | None) -> dict[str, Any]:
        revenue = func.sum(SalesOrderItem.quantity * SalesOrderItem.unit_price - SalesOrderItem.discount_amount)
        statement = select(SalesOrder.id, SalesOrder.order_number, SalesOrder.order_date, SalesOrder.status, SalesOrder.currency, Customer.company_name.label("customer"), revenue.label("revenue")).join(Customer).join(SalesOrderItem).group_by(SalesOrder.id, Customer.company_name)
        count_statement = select(func.count()).select_from(SalesOrder)
        if status_filter:
            statement = statement.where(SalesOrder.status == status_filter)
            count_statement = count_statement.where(SalesOrder.status == status_filter)
        if customer:
            pattern = f"%{customer.strip()}%"
            statement = statement.where(Customer.company_name.ilike(pattern))
            count_statement = count_statement.join(Customer).where(Customer.company_name.ilike(pattern))
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"order_date": SalesOrder.order_date, "order_number": SalesOrder.order_number, "revenue": revenue, "status": SalesOrder.status})
        monthly: dict[str, Decimal] = defaultdict(Decimal)
        chart_rows = self.db.execute(select(SalesOrder.order_date, SalesOrderItem.quantity * SalesOrderItem.unit_price - SalesOrderItem.discount_amount).join(SalesOrderItem).where(SalesOrder.status != "cancelled"))
        for order_date, amount in chart_rows:
            monthly[order_date.strftime("%Y-%m")] += amount
        return {"items": items, "pagination": pagination, "chart_data": [{"label": label, "value": value} for label, value in sorted(monthly.items())]}

    def finance(self, page: int, page_size: int, sort_by: str, sort_order: str, transaction_type: str | None, account_type: str | None) -> dict[str, Any]:
        statement = select(FinanceTransaction.id, FinanceTransaction.transaction_date, FinanceTransaction.transaction_type, FinanceTransaction.amount, FinanceTransaction.currency, FinanceTransaction.description, FinanceAccount.account_code, FinanceAccount.name.label("account_name"), FinanceAccount.account_type).join(FinanceAccount)
        count_statement = select(func.count()).select_from(FinanceTransaction).join(FinanceAccount)
        if transaction_type:
            statement = statement.where(FinanceTransaction.transaction_type == transaction_type)
            count_statement = count_statement.where(FinanceTransaction.transaction_type == transaction_type)
        if account_type:
            statement = statement.where(FinanceAccount.account_type == account_type)
            count_statement = count_statement.where(FinanceAccount.account_type == account_type)
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"transaction_date": FinanceTransaction.transaction_date, "amount": FinanceTransaction.amount, "account": FinanceAccount.account_code, "transaction_type": FinanceTransaction.transaction_type})
        signed_amount = func.sum(case((FinanceTransaction.transaction_type == "debit", -FinanceTransaction.amount), else_=FinanceTransaction.amount))
        chart = self.db.execute(select(FinanceAccount.account_type.label("label"), signed_amount.label("value")).join(FinanceTransaction).group_by(FinanceAccount.account_type).order_by(FinanceAccount.account_type)).mappings().all()
        return {"items": items, "pagination": pagination, "chart_data": [dict(row) for row in chart]}

    def inventory(self, page: int, page_size: int, sort_by: str, sort_order: str, warehouse: str | None, low_stock: bool | None) -> dict[str, Any]:
        available = InventoryStock.quantity_on_hand - InventoryStock.quantity_reserved
        statement = select(InventoryStock.id, Product.sku, Product.name.label("product"), Warehouse.code.label("warehouse_code"), Warehouse.name.label("warehouse"), InventoryStock.quantity_on_hand, InventoryStock.quantity_reserved, available.label("available"), Product.reorder_level).join(Product).join(Warehouse)
        count_statement = select(func.count()).select_from(InventoryStock).join(Product).join(Warehouse)
        if warehouse:
            statement = statement.where(Warehouse.code == warehouse)
            count_statement = count_statement.where(Warehouse.code == warehouse)
        if low_stock is True:
            statement = statement.where(InventoryStock.quantity_on_hand <= Product.reorder_level)
            count_statement = count_statement.where(InventoryStock.quantity_on_hand <= Product.reorder_level)
        elif low_stock is False:
            statement = statement.where(InventoryStock.quantity_on_hand > Product.reorder_level)
            count_statement = count_statement.where(InventoryStock.quantity_on_hand > Product.reorder_level)
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"available": available, "product": Product.name, "quantity_on_hand": InventoryStock.quantity_on_hand, "warehouse": Warehouse.code})
        chart = self.db.execute(select(Warehouse.code.label("label"), func.sum(available).label("value")).join(InventoryStock).group_by(Warehouse.code).order_by(Warehouse.code)).mappings().all()
        return {"items": items, "pagination": pagination, "chart_data": [dict(row) for row in chart]}

    def support(self, page: int, page_size: int, sort_by: str, sort_order: str, ticket_status: str | None, priority: str | None) -> dict[str, Any]:
        statement = select(SupportTicket.id, SupportTicket.ticket_number, SupportTicket.subject, SupportTicket.priority, SupportTicket.status, SupportTicket.opened_at, SupportTicket.resolved_at, Customer.company_name.label("customer")).join(Customer)
        count_statement = select(func.count()).select_from(SupportTicket)
        if ticket_status:
            statement = statement.where(SupportTicket.status == ticket_status)
            count_statement = count_statement.where(SupportTicket.status == ticket_status)
        if priority:
            statement = statement.where(SupportTicket.priority == priority)
            count_statement = count_statement.where(SupportTicket.priority == priority)
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"opened_at": SupportTicket.opened_at, "priority": SupportTicket.priority, "status": SupportTicket.status, "ticket_number": SupportTicket.ticket_number})
        chart = self.db.execute(select(SupportTicket.status.label("label"), func.count().label("value")).group_by(SupportTicket.status).order_by(SupportTicket.status)).mappings().all()
        return {"items": items, "pagination": pagination, "chart_data": [dict(row) for row in chart]}

    def employees(self, page: int, page_size: int, sort_by: str, sort_order: str, department: str | None, employment_status: str | None) -> dict[str, Any]:
        statement = select(Employee.id, Employee.employee_number, Employee.first_name, Employee.last_name, Employee.email, Employee.job_title, Employee.hire_date, Employee.salary, Employee.employment_status, Department.name.label("department")).join(Department)
        count_statement = select(func.count()).select_from(Employee).join(Department)
        if department:
            statement = statement.where(Department.code == department)
            count_statement = count_statement.where(Department.code == department)
        if employment_status:
            statement = statement.where(Employee.employment_status == employment_status)
            count_statement = count_statement.where(Employee.employment_status == employment_status)
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"employee_number": Employee.employee_number, "hire_date": Employee.hire_date, "last_name": Employee.last_name, "salary": Employee.salary})
        chart = self.db.execute(select(Department.name.label("label"), func.count(Employee.id).label("value")).join(Employee).group_by(Department.name).order_by(Department.name)).mappings().all()
        return {"items": items, "pagination": pagination, "chart_data": [dict(row) for row in chart]}

    def customers(self, page: int, page_size: int, sort_by: str, sort_order: str, region: str | None, customer_status: str | None, search: str | None) -> dict[str, Any]:
        statement = select(Customer.id, Customer.customer_number, Customer.company_name, Customer.industry, Customer.email, Customer.phone, Customer.country, Customer.region, Customer.status, Customer.created_at)
        count_statement = select(func.count()).select_from(Customer)
        if region:
            statement = statement.where(Customer.region == region)
            count_statement = count_statement.where(Customer.region == region)
        if customer_status:
            statement = statement.where(Customer.status == customer_status)
            count_statement = count_statement.where(Customer.status == customer_status)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(Customer.company_name.ilike(pattern))
            count_statement = count_statement.where(Customer.company_name.ilike(pattern))
        items, pagination = self._paginate(statement, count_statement, page, page_size, sort_by, sort_order, {"company_name": Customer.company_name, "created_at": Customer.created_at, "customer_number": Customer.customer_number, "region": Customer.region})
        chart = self.db.execute(select(Customer.region.label("label"), func.count().label("value")).group_by(Customer.region).order_by(Customer.region)).mappings().all()
        return {"items": items, "pagination": pagination, "chart_data": [dict(row) for row in chart]}
