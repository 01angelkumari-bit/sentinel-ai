from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    customer_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    region: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    sales_orders: Mapped[list[SalesOrder]] = relationship(back_populates="customer")
    support_tickets: Mapped[list[SupportTicket]] = relationship(back_populates="customer")


class ProductCategory(TimestampMixin, Base):
    __tablename__ = "product_categories"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    sku: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("product_categories.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[ProductCategory] = relationship(back_populates="products")
    suppliers: Mapped[list[ProductSupplier]] = relationship(back_populates="product", cascade="all, delete-orphan")
    inventory: Mapped[list[InventoryStock]] = relationship(back_populates="product")
    __table_args__ = (CheckConstraint("unit_cost >= 0 AND unit_price >= unit_cost", name="ck_products_valid_pricing"),)


class Supplier(TimestampMixin, Base):
    __tablename__ = "suppliers"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    supplier_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    products: Mapped[list[ProductSupplier]] = relationship(back_populates="supplier", cascade="all, delete-orphan")


class ProductSupplier(Base):
    __tablename__ = "product_suppliers"
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    supplier_id: Mapped[UUID] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True)
    supplier_sku: Mapped[str] = mapped_column(String(60), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    product: Mapped[Product] = relationship(back_populates="suppliers")
    supplier: Mapped[Supplier] = relationship(back_populates="products")


class Warehouse(TimestampMixin, Base):
    __tablename__ = "warehouses"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    capacity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    inventory: Mapped[list[InventoryStock]] = relationship(back_populates="warehouse")


class InventoryStock(TimestampMixin, Base):
    __tablename__ = "inventory_stock"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    warehouse_id: Mapped[UUID] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quantity_reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warehouse: Mapped[Warehouse] = relationship(back_populates="inventory")
    product: Mapped[Product] = relationship(back_populates="inventory")
    movements: Mapped[list[InventoryMovement]] = relationship(back_populates="stock")
    __table_args__ = (UniqueConstraint("warehouse_id", "product_id", name="uq_inventory_warehouse_product"), CheckConstraint("quantity_on_hand >= 0 AND quantity_reserved >= 0", name="ck_inventory_nonnegative"))


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    stock_id: Mapped[UUID] = mapped_column(ForeignKey("inventory_stock.id"), index=True, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    reference: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stock: Mapped[InventoryStock] = relationship(back_populates="movements")


class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    employees: Mapped[list[Employee]] = relationship(back_populates="department")


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    employee_number: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    department_id: Mapped[UUID] = mapped_column(ForeignKey("departments.id"), index=True, nullable=False)
    manager_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    job_title: Mapped[str] = mapped_column(String(120), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    employment_status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    department: Mapped[Department] = relationship(back_populates="employees")
    manager: Mapped[Employee | None] = relationship(remote_side="Employee.id", back_populates="direct_reports")
    direct_reports: Mapped[list[Employee]] = relationship(back_populates="manager")


class SalesOrder(TimestampMixin, Base):
    __tablename__ = "sales_orders"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    sales_rep_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    order_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    customer: Mapped[Customer] = relationship(back_populates="sales_orders")
    sales_rep: Mapped[Employee] = relationship()
    items: Mapped[list[SalesOrderItem]] = relationship(back_populates="order", cascade="all, delete-orphan")
    finance_transactions: Mapped[list[FinanceTransaction]] = relationship(back_populates="sales_order")


class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    sales_order_id: Mapped[UUID] = mapped_column(ForeignKey("sales_orders.id", ondelete="CASCADE"), index=True, nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), index=True, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    order: Mapped[SalesOrder] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price >= 0 AND discount_amount >= 0", name="ck_sales_item_values"),)


class FinanceAccount(TimestampMixin, Base):
    __tablename__ = "finance_accounts"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    transactions: Mapped[list[FinanceTransaction]] = relationship(back_populates="account")


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("finance_accounts.id"), index=True, nullable=False)
    sales_order_id: Mapped[UUID | None] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(String(240), nullable=False)
    account: Mapped[FinanceAccount] = relationship(back_populates="transactions")
    sales_order: Mapped[SalesOrder | None] = relationship(back_populates="finance_transactions")


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    ticket_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(ForeignKey("products.id"), index=True)
    assigned_employee_id: Mapped[UUID | None] = mapped_column(ForeignKey("employees.id"), index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    customer: Mapped[Customer] = relationship(back_populates="support_tickets")
    product: Mapped[Product | None] = relationship()
    assigned_employee: Mapped[Employee | None] = relationship()


class Report(TimestampMixin, Base):
    __tablename__ = "reports"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    report_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    created_by_employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    report_type: Mapped[str] = mapped_column(String(40), nullable=False)
    schedule: Mapped[str | None] = mapped_column(String(40))
    configuration_json: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[Employee] = relationship()


Index("ix_sales_orders_date_status", SalesOrder.order_date, SalesOrder.status)
Index("ix_finance_transactions_date_account", FinanceTransaction.transaction_date, FinanceTransaction.account_id)
