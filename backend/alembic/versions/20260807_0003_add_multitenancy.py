"""add organization tenancy, RBAC, and PostgreSQL RLS

Revision ID: 20260807_0003
Revises: 20260807_0002
"""
from uuid import UUID
from alembic import op
import sqlalchemy as sa

revision = "20260807_0003"
down_revision = "20260807_0002"
branch_labels = None
depends_on = None

DEMO_ORG = UUID("00000000-0000-0000-0000-000000000001")
BUSINESS_TABLES = [
    "customers", "product_categories", "products", "suppliers", "product_suppliers",
    "warehouses", "inventory_stock", "inventory_movements", "departments", "employees",
    "sales_orders", "sales_order_items", "finance_accounts", "finance_transactions",
    "support_tickets", "reports",
]

def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    organizations = sa.table("organizations", sa.column("id", sa.Uuid(as_uuid=True)), sa.column("name", sa.String()))
    op.bulk_insert(organizations, [{"id": DEMO_ORG, "name": "Sentinel AI Demo Organization"}])
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
        batch.add_column(sa.Column("role", sa.String(20), server_default="owner", nullable=False))
        batch.create_foreign_key("fk_users_organization", "organizations", ["organization_id"], ["id"], ondelete="RESTRICT")
        batch.create_index("ix_users_organization_id", ["organization_id"])
    op.execute(sa.text("UPDATE users SET organization_id = :org").bindparams(org=DEMO_ORG))
    with op.batch_alter_table("users") as batch:
        batch.alter_column("organization_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)

    for table in BUSINESS_TABLES + ["file_assets"]:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=True))
            batch.create_foreign_key(f"fk_{table}_organization", "organizations", ["organization_id"], ["id"], ondelete="CASCADE")
            batch.create_index(f"ix_{table}_organization_id", ["organization_id"])
        op.execute(sa.text(f"UPDATE {table} SET organization_id = :org").bindparams(org=DEMO_ORG))
        with op.batch_alter_table(table) as batch:
            batch.alter_column("organization_id", existing_type=sa.Uuid(as_uuid=True), nullable=False)

    if op.get_bind().dialect.name == "postgresql":
        for table in BUSINESS_TABLES + ["file_assets"]:
            op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
            op.execute(f'ALTER TABLE "{table}" FORCE ROW LEVEL SECURITY')
            op.execute(
                f'''CREATE POLICY {table}_tenant_isolation ON "{table}"
                USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)
                WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)'''
            )

def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        for table in BUSINESS_TABLES + ["file_assets"]:
            op.execute(f'DROP POLICY IF EXISTS {table}_tenant_isolation ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    for table in reversed(BUSINESS_TABLES + ["file_assets"]):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_organization_id")
            batch.drop_constraint(f"fk_{table}_organization", type_="foreignkey")
            batch.drop_column("organization_id")
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_organization_id")
        batch.drop_constraint("fk_users_organization", type_="foreignkey")
        batch.drop_column("role")
        batch.drop_column("organization_id")
    op.drop_table("organizations")
