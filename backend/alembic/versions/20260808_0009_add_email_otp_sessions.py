"""add email verification OTP challenges and revocable sessions

Revision ID: 20260808_0009
Revises: 20260808_0008
"""
from alembic import op
import sqlalchemy as sa

revision="20260808_0009"
down_revision="20260808_0008"
branch_labels=None
depends_on=None

def upgrade()->None:
    op.create_table("pending_registrations",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("email",sa.String(320),nullable=False,unique=True),sa.Column("full_name",sa.String(200),nullable=False),sa.Column("organization_name",sa.String(200),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("otp_hash",sa.String(64),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),sa.Column("last_sent_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False));op.create_index("ix_pending_registrations_email","pending_registrations",["email"],unique=True)
    op.create_table("otp_challenges",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("organization_id",sa.Uuid(),sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("email",sa.String(320),nullable=False),sa.Column("purpose",sa.String(20),nullable=False),sa.Column("otp_hash",sa.String(64),nullable=False),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("attempts",sa.Integer(),nullable=False,server_default="0"),sa.Column("consumed_at",sa.DateTime(timezone=True)),sa.Column("reset_token_hash",sa.String(64),unique=True),sa.Column("reset_token_expires_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.CheckConstraint("purpose IN ('login','password_reset')",name="ck_otp_challenge_purpose"));op.create_index("ix_otp_challenges_user_id","otp_challenges",["user_id"]);op.create_index("ix_otp_challenges_organization_id","otp_challenges",["organization_id"]);op.create_index("ix_otp_challenges_email","otp_challenges",["email"]);op.create_index("ix_otp_challenges_purpose","otp_challenges",["purpose"])
    op.create_table("auth_sessions",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("user_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("organization_id",sa.Uuid(),sa.ForeignKey("organizations.id",ondelete="CASCADE"),nullable=False),sa.Column("jti",sa.String(64),nullable=False,unique=True),sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False),sa.Column("revoked_at",sa.DateTime(timezone=True)),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False));op.create_index("ix_auth_sessions_user_id","auth_sessions",["user_id"]);op.create_index("ix_auth_sessions_organization_id","auth_sessions",["organization_id"]);op.create_index("ix_auth_sessions_jti","auth_sessions",["jti"],unique=True)

def downgrade()->None:
    op.drop_table("auth_sessions");op.drop_table("otp_challenges");op.drop_table("pending_registrations")
