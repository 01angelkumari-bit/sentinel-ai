"""Generate deterministic, relational BI demo data and optionally seed the database."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from faker import Faker
from sqlalchemy import Date as SADate, DateTime as SADateTime, Numeric as SANumeric, Uuid as SAUuid, delete

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.domain.business import models  # noqa: E402
from app.infrastructure.database import SessionLocal  # noqa: E402

SEED = 20260806
fake = Faker("en_US")
fake.seed_instance(SEED)
rng = random.Random(SEED)


def uid(entity: str, number: int | str) -> str:
    return str(uuid5(NAMESPACE_URL, f"sentinel-ai/{entity}/{number}"))


def money(value: float | Decimal) -> str:
    return f"{Decimal(str(value)).quantize(Decimal('0.01'))}"


def build_dataset() -> dict[str, list[dict[str, object]]]:
    data: dict[str, list[dict[str, object]]] = defaultdict(list)
    now = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
    start = now.date() - timedelta(days=364)

    categories = ["Analytics", "Automation", "Collaboration", "Compliance", "Data Infrastructure", "Finance", "Operations", "Security", "Support", "Workforce"]
    for i, name in enumerate(categories, 1):
        data["product_categories"].append({"id": uid("category", i), "name": name, "description": f"Enterprise {name.lower()} solutions and services."})

    departments = [
        ("EXEC", "Executive"), ("ENG", "Engineering"), ("FIN", "Finance"), ("HR", "People Operations"),
        ("OPS", "Operations"), ("SALES", "Sales"), ("SUP", "Customer Support"), ("MKT", "Marketing"),
    ]
    for i, (code, name) in enumerate(departments, 1):
        data["departments"].append({"id": uid("department", i), "code": code, "name": name})

    dept_jobs = {
        "EXEC": ["Chief Strategy Officer", "VP Business Operations"], "ENG": ["Software Engineer", "Data Engineer", "Platform Architect"],
        "FIN": ["Financial Analyst", "Accountant", "FP&A Manager"], "HR": ["People Partner", "Talent Specialist"],
        "OPS": ["Operations Analyst", "Supply Chain Manager"], "SALES": ["Account Executive", "Sales Manager", "Solutions Consultant"],
        "SUP": ["Support Specialist", "Customer Success Manager"], "MKT": ["Growth Manager", "Market Analyst"],
    }
    employee_ids: list[str] = []
    sales_ids: list[str] = []
    support_ids: list[str] = []
    dept_members: dict[str, list[str]] = defaultdict(list)
    used_emails: set[str] = set()
    for i in range(1, 201):
        dept_index = 0 if i <= 3 else rng.choices(range(1, 8), weights=[28, 12, 8, 18, 20, 9, 12], k=1)[0]
        dept_code, _ = departments[dept_index]
        employee_id = uid("employee", i)
        first, last = fake.first_name(), fake.last_name()
        email_base = f"{first}.{last}".lower().replace("'", "").replace(" ", ".")
        email = f"{email_base}@sentinel.example"
        if email in used_emails: email = f"{email_base}{i}@sentinel.example"
        used_emails.add(email)
        possible_managers = dept_members[dept_code][:3]
        manager_id = rng.choice(possible_managers) if possible_managers and i > 12 else None
        salary = rng.randint(48_000, 175_000)
        row = {"id": employee_id, "employee_number": f"EMP-{i:04d}", "department_id": uid("department", dept_index + 1), "manager_id": manager_id, "first_name": first, "last_name": last, "email": email, "job_title": rng.choice(dept_jobs[dept_code]), "hire_date": fake.date_between(start_date="-8y", end_date="-30d").isoformat(), "salary": money(salary), "employment_status": "active" if rng.random() > .04 else "leave"}
        data["employees"].append(row); employee_ids.append(employee_id); dept_members[dept_code].append(employee_id)
        if dept_code == "SALES": sales_ids.append(employee_id)
        if dept_code == "SUP": support_ids.append(employee_id)

    industries = ["Financial Services", "Healthcare", "Manufacturing", "Retail", "Technology", "Telecommunications", "Transportation", "Professional Services"]
    customer_ids: list[str] = []
    for i in range(1, 501):
        customer_id = uid("customer", i); customer_ids.append(customer_id)
        data["customers"].append({"id": customer_id, "customer_number": f"CUS-{i:05d}", "company_name": fake.unique.company(), "industry": rng.choice(industries), "email": f"procurement{i}@customer.example", "phone": fake.phone_number()[:40], "country": "United States", "region": rng.choice(["Northeast", "Southeast", "Midwest", "Southwest", "West"]), "status": rng.choices(["active", "prospect", "inactive"], weights=[84, 10, 6], k=1)[0]})

    supplier_ids: list[str] = []
    for i in range(1, 51):
        supplier_id = uid("supplier", i); supplier_ids.append(supplier_id)
        data["suppliers"].append({"id": supplier_id, "supplier_number": f"SUP-{i:04d}", "company_name": fake.unique.company(), "contact_name": fake.name(), "email": f"vendor{i}@supplier.example", "phone": fake.phone_number()[:40], "country": rng.choice(["United States", "Canada", "Germany", "India", "United Kingdom"]), "payment_terms_days": rng.choice([15, 30, 45, 60])})

    product_ids: list[str] = []
    product_prices: dict[str, Decimal] = {}
    product_names: dict[str, str] = {}
    adjectives = ["Adaptive", "Cloud", "Enterprise", "Insight", "Nexus", "Precision", "Quantum", "Secure", "Unified", "Velocity"]
    nouns = ["Console", "Engine", "Fabric", "Gateway", "Hub", "Monitor", "Platform", "Suite", "Workspace", "Workbench"]
    for i in range(1, 101):
        product_id = uid("product", i); product_ids.append(product_id)
        category_index = (i - 1) % len(categories)
        name = f"{adjectives[(i - 1) % 10]} {nouns[((i - 1) // 10) % 10]} {i:02d}"
        cost = Decimal(rng.randrange(2500, 85000)) / 100
        price = (cost * Decimal(str(rng.uniform(1.35, 2.4)))).quantize(Decimal("0.01"))
        product_prices[product_id] = price; product_names[product_id] = name
        data["products"].append({"id": product_id, "sku": f"SNT-{category_index + 1:02d}-{i:04d}", "category_id": uid("category", category_index + 1), "name": name, "description": f"{categories[category_index]} capability for mid-market and enterprise teams.", "unit_cost": money(cost), "unit_price": money(price), "reorder_level": rng.randint(10, 50), "is_active": True})
        chosen = rng.sample(supplier_ids, rng.randint(1, 3))
        for j, supplier_id in enumerate(chosen): data["product_suppliers"].append({"product_id": product_id, "supplier_id": supplier_id, "supplier_sku": f"V-{i:04d}-{j + 1}", "lead_time_days": rng.randint(3, 28), "preferred": j == 0})

    warehouse_ids: list[str] = []
    locations = [("New York", "United States"), ("Chicago", "United States"), ("Dallas", "United States"), ("Seattle", "United States"), ("Atlanta", "United States"), ("Toronto", "Canada"), ("London", "United Kingdom"), ("Frankfurt", "Germany"), ("Bengaluru", "India"), ("Singapore", "Singapore")]
    stock_ids: list[str] = []
    for i, (city, country) in enumerate(locations, 1):
        warehouse_id = uid("warehouse", i); warehouse_ids.append(warehouse_id)
        data["warehouses"].append({"id": warehouse_id, "code": f"WH-{i:02d}", "name": f"{city} Distribution Center", "city": city, "country": country, "capacity_units": rng.randrange(18_000, 65_000, 1000)})
        for p, product_id in enumerate(product_ids, 1):
            stock_id = uid("stock", f"{i}-{p}"); stock_ids.append(stock_id)
            on_hand = rng.randint(5, 180)
            data["inventory_stock"].append({"id": stock_id, "warehouse_id": warehouse_id, "product_id": product_id, "quantity_on_hand": on_hand, "quantity_reserved": rng.randint(0, min(25, on_hand))})
            if rng.random() < .32:
                data["inventory_movements"].append({"id": uid("movement", f"{i}-{p}"), "stock_id": stock_id, "movement_type": rng.choice(["receipt", "sale", "adjustment", "transfer"]), "quantity": rng.choice([-1, 1]) * rng.randint(1, 30), "reference": f"MOV-{i:02d}-{p:04d}", "occurred_at": fake.date_time_between(start_date=start, end_date=now, tzinfo=UTC).isoformat()})

    accounts = [("1000", "Operating Cash", "asset"), ("1200", "Accounts Receivable", "asset"), ("4000", "Product Revenue", "revenue"), ("4100", "Services Revenue", "revenue"), ("5000", "Cost of Goods Sold", "expense"), ("6100", "Payroll Expense", "expense"), ("6200", "Operating Expense", "expense")]
    for i, (code, name, account_type) in enumerate(accounts, 1): data["finance_accounts"].append({"id": uid("finance-account", i), "account_code": code, "name": name, "account_type": account_type})

    if not sales_ids: sales_ids = employee_ids
    order_counter = item_counter = finance_counter = 0
    for day_offset in range(365):
        order_date = start + timedelta(days=day_offset)
        daily_orders = rng.randint(3, 8) if order_date.weekday() < 5 else rng.randint(1, 3)
        for _ in range(daily_orders):
            order_counter += 1; order_id = uid("sales-order", order_counter)
            status = rng.choices(["completed", "shipped", "processing", "cancelled"], weights=[75, 12, 8, 5], k=1)[0]
            data["sales_orders"].append({"id": order_id, "order_number": f"SO-{order_date:%Y%m%d}-{order_counter:05d}", "customer_id": rng.choice(customer_ids), "sales_rep_id": rng.choice(sales_ids), "order_date": order_date.isoformat(), "status": status, "currency": "USD"})
            order_total = Decimal("0")
            for product_id in rng.sample(product_ids, rng.randint(1, 5)):
                item_counter += 1; quantity = rng.randint(1, 12); unit_price = product_prices[product_id]; discount = (unit_price * quantity * Decimal(str(rng.choice([0, 0, .05, .1, .15])))).quantize(Decimal("0.01"))
                data["sales_order_items"].append({"id": uid("sales-item", item_counter), "sales_order_id": order_id, "product_id": product_id, "quantity": quantity, "unit_price": money(unit_price), "discount_amount": money(discount)})
                order_total += unit_price * quantity - discount
            if status != "cancelled":
                finance_counter += 1
                data["finance_transactions"].append({"id": uid("finance-transaction", finance_counter), "account_id": uid("finance-account", 3), "sales_order_id": order_id, "transaction_date": order_date.isoformat(), "transaction_type": "credit", "amount": money(order_total), "currency": "USD", "description": f"Revenue recognized for sales order {order_counter}"})

    for i in range(1, 901):
        opened = fake.date_time_between(start_date=datetime.combine(start, time.min, tzinfo=UTC), end_date=now, tzinfo=UTC)
        status = rng.choices(["resolved", "closed", "open", "pending"], weights=[54, 25, 14, 7], k=1)[0]
        resolved = opened + timedelta(hours=rng.randint(1, 120)) if status in {"resolved", "closed"} else None
        product_id = rng.choice(product_ids)
        data["support_tickets"].append({"id": uid("ticket", i), "ticket_number": f"TKT-{i:06d}", "customer_id": rng.choice(customer_ids), "product_id": product_id, "assigned_employee_id": rng.choice(support_ids or employee_ids), "subject": rng.choice([f"Configuration assistance for {product_names[product_id]}", "Data synchronization delay", "Access policy clarification", "Dashboard metric discrepancy", "Integration connection issue"]), "priority": rng.choices(["low", "medium", "high", "critical"], weights=[24, 48, 22, 6], k=1)[0], "status": status, "opened_at": opened.isoformat(), "resolved_at": resolved.isoformat() if resolved else None})

    for i in range(1, 25):
        report_type = rng.choice(["sales", "inventory", "finance", "support", "workforce"])
        data["reports"].append({"id": uid("report", i), "report_code": f"RPT-{i:04d}", "created_by_employee_id": rng.choice(employee_ids), "name": f"{report_type.title()} {rng.choice(['Executive Summary', 'Trend Analysis', 'Operational Review', 'Forecast'])}", "report_type": report_type, "schedule": rng.choice(["daily", "weekly", "monthly", None]), "configuration_json": json.dumps({"period": "rolling_12_months", "currency": "USD", "include_variance": True}, separators=(",", ":")), "is_active": rng.random() > .08})

    return dict(data)


def write_csv_files(dataset: dict[str, list[dict[str, object]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for table, rows in dataset.items():
        if not rows: continue
        with (output_dir / f"{table}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)


def seed_database(dataset: dict[str, list[dict[str, object]]], reset: bool) -> None:
    table_order = ["product_categories", "departments", "customers", "suppliers", "warehouses", "finance_accounts", "employees", "products", "product_suppliers", "inventory_stock", "inventory_movements", "sales_orders", "sales_order_items", "finance_transactions", "support_tickets", "reports"]
    model_by_table = {mapper.local_table.name: mapper.class_ for mapper in models.Base.registry.mappers if mapper.local_table.name in table_order}
    with SessionLocal() as session:
        if reset:
            for table in reversed(table_order): session.execute(delete(model_by_table[table]))
        for table in table_order:
            model = model_by_table[table]
            columns = {column.name: column for column in model.__table__.columns}
            normalized_rows = []
            for row in dataset.get(table, []):
                normalized = dict(row)
                for key, value in row.items():
                    if value is None or key not in columns: continue
                    column_type = columns[key].type
                    if isinstance(column_type, SAUuid) and isinstance(value, str): normalized[key] = UUID(value)
                    elif isinstance(column_type, SADateTime) and isinstance(value, str): normalized[key] = datetime.fromisoformat(value)
                    elif isinstance(column_type, SADate) and not isinstance(column_type, SADateTime) and isinstance(value, str): normalized[key] = date.fromisoformat(value)
                    elif isinstance(column_type, SANumeric) and isinstance(value, str): normalized[key] = Decimal(value)
                normalized_rows.append(normalized)
            if normalized_rows: session.bulk_insert_mappings(model, normalized_rows)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "csv")
    parser.add_argument("--database", action="store_true", help="Insert generated rows into configured DATABASE_URL")
    parser.add_argument("--reset", action="store_true", help="Delete existing BI rows before database seeding")
    args = parser.parse_args()
    dataset = build_dataset(); write_csv_files(dataset, args.output)
    if args.database: seed_database(dataset, args.reset)
    print(json.dumps({table: len(rows) for table, rows in dataset.items()}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
