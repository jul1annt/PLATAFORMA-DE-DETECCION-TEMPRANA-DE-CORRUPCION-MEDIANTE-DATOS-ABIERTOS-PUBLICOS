"""Add durable background jobs for long running operations.

Revision ID: 7b2acfd82e41
Revises: 0a9de53a38b9
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "7b2acfd82e41"
down_revision = "0a9de53a38b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("public_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_key", sa.String(length=160), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDIENTE", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("public_id"),
    )
    op.create_index("ix_background_jobs_dispatch", "background_jobs", ["status", "created_at"])
    op.create_index(
        "uq_background_jobs_active_resource",
        "background_jobs",
        ["resource_key"],
        unique=True,
        postgresql_where=sa.text("resource_key IS NOT NULL AND active IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_background_jobs_active_resource", table_name="background_jobs")
    op.drop_index("ix_background_jobs_dispatch", table_name="background_jobs")
    op.drop_table("background_jobs")
