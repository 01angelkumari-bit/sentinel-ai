"""enforce supported RBAC roles

Revision ID: 20260807_0005
Revises: 20260807_0004
"""
from alembic import op

revision = "20260807_0005"
down_revision = "20260807_0004"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.create_check_constraint("ck_users_valid_role", "role IN ('owner','admin','manager','employee','viewer')")

def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("ck_users_valid_role", type_="check")
