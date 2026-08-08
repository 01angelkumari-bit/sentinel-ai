"""isolate legacy users that predate organization membership

Revision ID: 20260807_0004
Revises: 20260807_0003
"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "20260807_0004"
down_revision = "20260807_0003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id, full_name FROM users ORDER BY created_at, id")).mappings().all()
    for user in users[1:]:
        organization_id = uuid4()
        bound_id = organization_id.hex if connection.dialect.name == "sqlite" else organization_id
        connection.execute(
            sa.text("INSERT INTO organizations (id, name) VALUES (:id, :name)"),
            {"id": bound_id, "name": f"{user['full_name']}'s Organization"[:200]},
        )
        connection.execute(
            sa.text("UPDATE users SET organization_id = :organization_id, role = 'owner' WHERE id = :user_id"),
            {"organization_id": bound_id, "user_id": user["id"]},
        )

def downgrade() -> None:
    connection = op.get_bind()
    demo = "00000000000000000000000000000001" if connection.dialect.name == "sqlite" else "00000000-0000-0000-0000-000000000001"
    connection.execute(sa.text("UPDATE users SET organization_id = :demo"), {"demo": demo})
    connection.execute(sa.text("DELETE FROM organizations WHERE id != :demo"), {"demo": demo})
