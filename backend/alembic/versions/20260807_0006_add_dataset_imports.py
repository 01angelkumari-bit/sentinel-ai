"""add tenant dataset import jobs and history

Revision ID: 20260807_0006
Revises: 20260807_0005
"""
from alembic import op
import sqlalchemy as sa

revision = "20260807_0006"
down_revision = "20260807_0005"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "dataset_imports",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("organization_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("file_asset_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("mode", sa.String(12), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("total_rows", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("imported_rows", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("mode IN ('initial','append','replace')", name="ck_dataset_import_mode"),
        sa.CheckConstraint("status IN ('queued','processing','completed','failed')", name="ck_dataset_import_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_dataset_imports_organization_id", "dataset_imports", ["organization_id"])
    op.create_index("ix_dataset_imports_status", "dataset_imports", ["status"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute('ALTER TABLE "dataset_imports" ENABLE ROW LEVEL SECURITY')
        op.execute('ALTER TABLE "dataset_imports" FORCE ROW LEVEL SECURITY')
        op.execute("""CREATE POLICY dataset_imports_tenant_isolation ON dataset_imports
            USING (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)
            WITH CHECK (organization_id = NULLIF(current_setting('app.current_organization', true), '')::uuid)""")

def downgrade() -> None:
    op.drop_index("ix_dataset_imports_status", table_name="dataset_imports")
    op.drop_index("ix_dataset_imports_organization_id", table_name="dataset_imports")
    op.drop_table("dataset_imports")
