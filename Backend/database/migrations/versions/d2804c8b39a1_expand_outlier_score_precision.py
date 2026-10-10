"""Allow large outlier scores in full SECOP analyses."""

from alembic import op
import sqlalchemy as sa


revision = "d2804c8b39a1"
down_revision = "b1a5d2e3c4f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "contrato_outlier",
        "score",
        existing_type=sa.Numeric(precision=10, scale=4),
        type_=sa.Numeric(precision=38, scale=4),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM contrato_outlier
                WHERE score > 999999.9999 OR score < -999999.9999
            ) THEN
                RAISE EXCEPTION
                    'No se puede reducir score a NUMERIC(10,4): hay valores fuera de rango';
            END IF;
        END
        $$;
        """
    )
    op.alter_column(
        "contrato_outlier",
        "score",
        existing_type=sa.Numeric(precision=38, scale=4),
        type_=sa.Numeric(precision=10, scale=4),
        existing_nullable=False,
    )
