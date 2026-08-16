"""optimize authentication indexes

Revision ID: 20260816_0010
Revises: 20260808_0009
"""
from alembic import op

revision = "20260816_0010"
down_revision = "20260808_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at"], unique=False)
    op.create_index("ix_auth_sessions_org_user_active", "auth_sessions", ["organization_id", "user_id", "revoked_at"], unique=False)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_org_user_active", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_active", table_name="auth_sessions")
