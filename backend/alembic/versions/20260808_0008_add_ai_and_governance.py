"""add tenant chat, invitations, audit logs, and report schedules

Revision ID: 20260808_0008
Revises: 20260807_0007
"""
from alembic import op
import sqlalchemy as sa

revision = "20260808_0008"
down_revision = "20260807_0007"
branch_labels = None
depends_on = None


def _tenant_columns() -> list[sa.Column]:
    return [sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)]


def upgrade() -> None:
    op.create_table("chat_conversations", *_tenant_columns(), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_chat_conversations_organization_id", "chat_conversations", ["organization_id"]); op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"])
    op.create_table("chat_messages", *_tenant_columns(), sa.Column("conversation_id", sa.Uuid(), sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("role", sa.String(12), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.CheckConstraint("role IN ('user','assistant')", name="ck_chat_messages_role"))
    op.create_index("ix_chat_messages_organization_id", "chat_messages", ["organization_id"]); op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_table("audit_logs", *_tenant_columns(), sa.Column("actor_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL")), sa.Column("action", sa.String(80), nullable=False), sa.Column("resource_type", sa.String(50), nullable=False), sa.Column("resource_id", sa.String(80)), sa.Column("detail", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"]); op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"]); op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_table("organization_invitations", *_tenant_columns(), sa.Column("invited_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(320), nullable=False), sa.Column("role", sa.String(20), nullable=False), sa.Column("token_hash", sa.String(64), unique=True, nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("accepted_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_organization_invitations_organization_id", "organization_invitations", ["organization_id"]); op.create_index("ix_organization_invitations_email", "organization_invitations", ["email"])
    op.create_table("report_schedules", *_tenant_columns(), sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("frequency", sa.String(20), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_run_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_report_schedules_organization_id", "report_schedules", ["organization_id"])


def downgrade() -> None:
    for table in ("report_schedules", "organization_invitations", "audit_logs", "chat_messages", "chat_conversations"):
        op.drop_table(table)
