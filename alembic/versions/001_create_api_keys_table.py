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
    conn = op.get_bind()

    result = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'tierenum'"))
    if not result.scalar():
        tier_enum = sa.Enum("free", "pro", "enterprise", name="tierenum", create_type=False)
        tier_enum.create(conn)

    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'api_keys'")
    )
    if not result.scalar():
        op.create_table(
            "api_keys",
            sa.Column("key", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column(
                "tier", sa.Enum("free", "pro", "enterprise", name="tierenum", create_type=False), nullable=False
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("requests_today", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("key"),
        )
        op.create_index(op.f("ix_api_keys_email"), "api_keys", ["email"], unique=False)
        op.create_index(op.f("ix_api_keys_key"), "api_keys", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_api_keys_key"), table_name="api_keys")
    op.drop_index(op.f("ix_api_keys_email"), table_name="api_keys")
    op.drop_table("api_keys")
    sa.Enum("free", "pro", "enterprise", name="tierenum", create_type=False).drop(op.get_bind())
