"""create api keys table

Revision ID: 001_create_api_keys_table
Revises:
Create Date: 2026-03-16 10:12:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "001_create_api_keys_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("tier", sa.String(10), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("requests_today", sa.String(), nullable=True),
        sa.CheckConstraint("tier IN ('free','pro','enterprise')", name="ck_api_keys_tier"),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_api_keys_key", "api_keys", ["key"], unique=False)
    op.create_index("ix_api_keys_email", "api_keys", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_api_keys_email", table_name="api_keys")
    op.drop_index("ix_api_keys_key", table_name="api_keys")
    op.drop_table("api_keys")
