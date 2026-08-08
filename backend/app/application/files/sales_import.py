from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
import pandas as pd

from app.domain.business.models import Customer, Department, Employee, FinanceAccount, FinanceTransaction, InventoryMovement, InventoryStock, Product, ProductCategory, ProductSupplier, Report, SalesOrder, SalesOrderItem, Supplier, SupportTicket, Warehouse

SALES_COLUMNS = {"Date", "Revenue", "Orders", "Cancelled", "Region", "Product", "Customer"}


def normalize_sales_file(filename: str, data: bytes) -> tuple[bytes, int, list[dict[str, str]]]:
    """Validate CSV/XLSX and return the canonical UTF-8 CSV representation."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        count, preview = inspect_sales_csv(data)
        return data, count, preview
    if suffix != ".xlsx":
        raise HTTPException(status_code=415, detail="Dataset onboarding accepts CSV or XLSX files")
    if not data.startswith(b"PK"):
        raise HTTPException(status_code=422, detail="The Excel workbook signature is invalid")
    try:
        frame = pd.read_excel(io.BytesIO(data), engine="openpyxl")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="The Excel workbook could not be read") from exc
    if not SALES_COLUMNS.issubset(set(frame.columns)):
        raise HTTPException(status_code=422, detail="Excel must include: Date,Revenue,Orders,Cancelled,Region,Product,Customer")
    if frame.empty:
        raise HTTPException(status_code=422, detail="The Excel workbook contains no business records")
    if len(frame) > 100_000:
        raise HTTPException(status_code=413, detail="Excel is limited to 100,000 records per import")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise").dt.date.astype(str)
    canonical = frame.to_csv(index=False).encode("utf-8")
    count, preview = inspect_sales_csv(canonical)
    return canonical, count, preview

def inspect_sales_csv(data: bytes) -> tuple[int, list[dict[str, str]]]:
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV files must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(decoded))
    if not SALES_COLUMNS.issubset(set(reader.fieldnames or [])):
        raise HTTPException(status_code=422, detail="CSV must include: Date,Revenue,Orders,Cancelled,Region,Product,Customer")
    preview, count = [], 0
    for row in reader:
        count += 1
        if len(preview) < 5:
            preview.append({key: value or "" for key, value in row.items()})
    if count == 0:
        raise HTTPException(status_code=422, detail="Sales CSV contains no data rows")
    if count > 100_000:
        raise HTTPException(status_code=413, detail="CSV is limited to 100,000 records per import")
    return count, preview

class SalesCsvImporter:
    """Import the documented aggregate Sales.csv format into tenant-owned normalized records."""

    def __init__(self, db: Session, organization_id: UUID) -> None:
        self.db = db
        self.organization_id = organization_id
        self.prefix = organization_id.hex[:10]

    def import_if_supported(self, content_type: str, data: bytes, *, replace: bool = False, progress=None) -> int:
        if content_type != "text/csv":
            return 0
        try:
            decoded = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="CSV files must use UTF-8 encoding") from exc
        reader = csv.DictReader(io.StringIO(decoded))
        columns = set(reader.fieldnames or [])
        if not SALES_COLUMNS.issubset(columns):
            return 0
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=422, detail="Sales CSV contains no data rows")
        if len(rows) > 100_000:
            raise HTTPException(status_code=413, detail="Sales CSV is limited to 100,000 rows per import")
        try:
            if replace:
                delete_tenant_business_data(self.db, self.organization_id)
            category, department, employee = self._defaults()
            self.customers = {item.company_name: item for item in self.db.scalars(select(Customer).where(Customer.organization_id == self.organization_id))}
            self.products = {item.name: item for item in self.db.scalars(select(Product).where(Product.organization_id == self.organization_id))}
            imported = 0
            for index, row in enumerate(rows, start=2):
                imported += self._import_row(row, index, category, employee)
                if index % 500 == 0:
                    self.db.flush()
                    if progress:
                        progress(index - 1, len(rows))
            self.db.commit()
            if progress:
                progress(len(rows), len(rows))
            return imported
        except HTTPException:
            self.db.rollback(); raise
        except Exception as exc:
            self.db.rollback()
            raise HTTPException(status_code=422, detail="Sales CSV could not be imported safely") from exc

    def _defaults(self) -> tuple[ProductCategory, Department, Employee]:
        category = self.db.scalar(select(ProductCategory).where(ProductCategory.organization_id == self.organization_id, ProductCategory.name == f"Imported Sales {self.prefix}"))
        if not category:
            category = ProductCategory(organization_id=self.organization_id, name=f"Imported Sales {self.prefix}", description="Products created from tenant CSV imports")
            self.db.add(category)
        department = self.db.scalar(select(Department).where(Department.organization_id == self.organization_id, Department.code == f"IMP-{self.prefix}"))
        if not department:
            department = Department(organization_id=self.organization_id, code=f"IMP-{self.prefix}", name=f"Imported Sales {self.prefix}")
            self.db.add(department)
        self.db.flush()
        employee = self.db.scalar(select(Employee).where(Employee.organization_id == self.organization_id, Employee.employee_number == f"IMP-{self.prefix}"))
        if not employee:
            employee = Employee(organization_id=self.organization_id, employee_number=f"IMP-{self.prefix}", department_id=department.id, first_name="CSV", last_name="Importer", email=f"csv-importer-{self.prefix}@sentinel.local", job_title="Data Import Service", hire_date=date.today(), salary=Decimal("0"), employment_status="active")
            self.db.add(employee); self.db.flush()
        return category, department, employee

    def _import_row(self, row: dict[str, str | None], line: int, category: ProductCategory, employee: Employee) -> int:
        try:
            order_date = date.fromisoformat((row.get("Date") or "").strip())
            revenue = Decimal((row.get("Revenue") or "0").replace(",", "").replace("₹", "").replace("$", "").strip())
            orders = int((row.get("Orders") or "0").strip())
            cancelled = int((row.get("Cancelled") or "0").strip())
        except (ValueError, InvalidOperation) as exc:
            raise HTTPException(status_code=422, detail=f"Invalid numeric or date value on CSV line {line}") from exc
        recognized_orders = orders - cancelled
        if revenue < 0 or orders < 0 or cancelled < 0 or cancelled > orders:
            raise HTTPException(status_code=422, detail=f"Out-of-range value on CSV line {line}")
        if recognized_orders == 0:
            return 0
        customer_name = (row.get("Customer") or "").strip()
        product_name = (row.get("Product") or "").strip()
        region = (row.get("Region") or "Unknown").strip() or "Unknown"
        if not customer_name or not product_name:
            raise HTTPException(status_code=422, detail=f"Customer and Product are required on CSV line {line}")
        customer = self.customers.get(customer_name)
        if not customer:
            token = uuid4().hex[:12]
            customer = Customer(organization_id=self.organization_id, customer_number=f"CSV-{self.prefix}-{token}", company_name=customer_name[:200], industry="Imported", email=f"customer-{self.prefix}-{token}@import.sentinel", country="Unknown", region=region[:80], status="active")
            self.db.add(customer)
            self.customers[customer_name] = customer
        product = self.products.get(product_name)
        unit_price = (revenue / recognized_orders).quantize(Decimal("0.01"))
        if not product:
            token = uuid4().hex[:12]
            product = Product(organization_id=self.organization_id, sku=f"CSV-{self.prefix}-{token}", category_id=category.id, name=product_name[:180], unit_cost=(unit_price * Decimal("0.60")).quantize(Decimal("0.01")), unit_price=unit_price, reorder_level=10, is_active=True)
            self.db.add(product)
            self.products[product_name] = product
        self.db.flush()
        order = SalesOrder(organization_id=self.organization_id, order_number=f"CSV-{self.prefix}-{uuid4().hex[:16]}", customer_id=customer.id, sales_rep_id=employee.id, order_date=order_date, status="completed", currency="USD")
        self.db.add(order); self.db.flush()
        self.db.add(SalesOrderItem(organization_id=self.organization_id, sales_order_id=order.id, product_id=product.id, quantity=recognized_orders, unit_price=unit_price, discount_amount=Decimal("0")))
        return 1


def delete_tenant_business_data(db: Session, organization_id: UUID) -> None:
    """Delete one tenant's normalized dataset in foreign-key-safe order."""
    for model in (FinanceTransaction, SalesOrderItem, SupportTicket, InventoryMovement, SalesOrder, InventoryStock, ProductSupplier, Report, Product, Customer, Supplier, Warehouse, Employee, Department, FinanceAccount, ProductCategory):
        db.execute(delete(model).where(model.organization_id == organization_id))
    db.flush()
