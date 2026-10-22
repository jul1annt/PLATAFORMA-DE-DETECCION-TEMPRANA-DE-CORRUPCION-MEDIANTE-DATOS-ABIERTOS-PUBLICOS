"""Preserve prior SECOP row values whenever an upsert changes them.

Revision ID: c7e3a91b5d24
Revises: 9a14c6e2b570
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c7e3a91b5d24"
down_revision = "9a14c6e2b570"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_secop_historial",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("raw_secop_id", sa.BigInteger(), nullable=False),
        sa.Column("id_del_proceso", sa.String(length=100), nullable=True),
        sa.Column("fuente_id", sa.Integer(), nullable=False),
        sa.Column("datos_anteriores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("archivado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_raw_secop_historial_raw_id", "raw_secop_historial", ["raw_secop_id"]
    )
    op.create_index(
        "ix_raw_secop_historial_proceso", "raw_secop_historial", ["id_del_proceso"]
    )
    op.execute(
        sa.text(
            """
        CREATE FUNCTION archive_raw_secop_version() RETURNS trigger AS $$
        BEGIN
            IF (to_jsonb(OLD) - 'sincronizado_en') IS DISTINCT FROM
               (to_jsonb(NEW) - 'sincronizado_en') THEN
                INSERT INTO raw_secop_historial (
                    raw_secop_id, id_del_proceso, fuente_id, datos_anteriores
                ) VALUES (
                    OLD.id, OLD.id_del_proceso, OLD.fuente_id, to_jsonb(OLD)
                );
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
        )
    )
    op.execute(
        sa.text(
            """
        CREATE TRIGGER trg_archive_raw_secop_version
        BEFORE UPDATE ON raw_secop
        FOR EACH ROW EXECUTE FUNCTION archive_raw_secop_version()
        """
        )
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_archive_raw_secop_version ON raw_secop")
    op.execute("DROP FUNCTION IF EXISTS archive_raw_secop_version()")
    op.drop_index("ix_raw_secop_historial_proceso", table_name="raw_secop_historial")
    op.drop_index("ix_raw_secop_historial_raw_id", table_name="raw_secop_historial")
    op.drop_table("raw_secop_historial")
