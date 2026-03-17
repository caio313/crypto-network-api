"""create api keys table

Revision ID: 001_create_api_keys_table
Revises:
Create Date: 2026-03-16 10:12:00.000000

"""

from alembic import op
import sqlalchemy as sa
import enum


# revision identifiers, used by Alembic.
revision = "001_create_api_keys_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for tier
    tier_enum = sa.Enum("free", "pro", "enterprise", name="tierenum")
    tier_enum.create(op.get_bind())

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("tier", tier_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("requests_today", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # Create indexes
    op.create_index(op.f("ix_api_keys_email"), "api_keys", ["email"], unique=False)
    op.create_index(op.f("ix_api_keys_key"), "api_keys", ["key"], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f("ix_api_keys_key"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_email"), table_name="api_keys")

    # Drop table
    op.drop_table("api_keys")

    # Drop enum type
    sa.Enum("free", "pro", "enterprise", name="tierenum").drop(op.get_bind())
