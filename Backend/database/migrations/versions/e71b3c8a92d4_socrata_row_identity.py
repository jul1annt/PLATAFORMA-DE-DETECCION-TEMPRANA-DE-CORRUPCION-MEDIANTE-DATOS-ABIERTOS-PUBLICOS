"""Store each SECOP source row independently, including multiple awards per process.

Revision ID: e71b3c8a92d4
Revises: c7e3a91b5d24
"""
from alembic import op
import sqlalchemy as sa


revision = "e71b3c8a92d4"
down_revision = "c7e3a91b5d24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("raw_secop", sa.Column("socrata_row_id", sa.String(length=255), nullable=True))
    op.drop_index("ix_raw_secop_id_proceso", table_name="raw_secop")
    op.create_index("ix_raw_secop_id_proceso", "raw_secop", ["id_del_proceso"], unique=False)
    op.create_index(
        "ix_raw_secop_fuente_socrata_row_id",
        "raw_secop",
        ["fuente_id", "socrata_row_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_raw_secop_fuente_socrata_row_id", table_name="raw_secop")
    op.drop_index("ix_raw_secop_id_proceso", table_name="raw_secop")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM raw_secop
                WHERE id_del_proceso IS NOT NULL
                GROUP BY id_del_proceso HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION 'Cannot restore unique process index: raw_secop contains multiple rows per process';
            END IF;
        END $$;
        """
    )
    op.create_index("ix_raw_secop_id_proceso", "raw_secop", ["id_del_proceso"], unique=True)
    op.drop_column("raw_secop", "socrata_row_id")
