"""add persisted file assets

Revision ID: 20260807_0002
Revises: eeb2e3049ae4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260807_0002"
down_revision: Union[str, None] = "eeb2e3049ae4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "file_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("stored_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("relative_path", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relative_path"),
        sa.UniqueConstraint("stored_name"),
    )
    op.create_index("ix_file_assets_kind", "file_assets", ["kind"])
    op.create_index("ix_file_assets_owner_id", "file_assets", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_file_assets_owner_id", table_name="file_assets")
    op.drop_index("ix_file_assets_kind", table_name="file_assets")
    op.drop_table("file_assets")
