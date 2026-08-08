"""remove legacy shared demo data before dataset onboarding

Revision ID: 20260807_0007
Revises: 20260807_0006
"""
from alembic import op

revision = "20260807_0007"
down_revision = "20260807_0006"
branch_labels = None
depends_on = None

def upgrade() -> None:
    for table in ("dataset_imports", "finance_transactions", "sales_order_items", "support_tickets", "inventory_movements", "sales_orders", "inventory_stock", "product_suppliers", "reports", "products", "customers", "suppliers", "warehouses", "employees", "departments", "finance_accounts", "product_categories", "file_assets"):
        op.execute(f'DELETE FROM "{table}"')

def downgrade() -> None:
    # Removed synthetic/demo data is deliberately not recreated.
    pass
