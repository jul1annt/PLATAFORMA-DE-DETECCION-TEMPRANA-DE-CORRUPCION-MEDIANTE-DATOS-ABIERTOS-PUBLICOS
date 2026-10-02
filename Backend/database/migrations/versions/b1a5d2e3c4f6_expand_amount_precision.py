"""Allow SECOP monetary fields to preserve unusually large source amounts.

Revision ID: b1a5d2e3c4f6
Revises: e71b3c8a92d4
"""
from alembic import op
import sqlalchemy as sa


revision = "b1a5d2e3c4f6"
down_revision = "e71b3c8a92d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table, column in (
        ("raw_secop", "precio_base"),
        ("raw_secop", "valor_total_adjudicacion"),
        ("contratos_procesados", "valor_total_normalizado"),
        ("contratos_procesados", "precio_base_normalizado"),
        ("contrato_outlier", "valor"),
        ("contrato_outlier", "q1"),
        ("contrato_outlier", "q3"),
        ("contrato_outlier", "iqr"),
        ("contrato_outlier", "limite_inferior"),
        ("contrato_outlier", "limite_superior"),
    ):
        op.alter_column(
            table,
            column,
            existing_type=sa.Numeric(precision=20, scale=2),
            type_=sa.Numeric(precision=38, scale=2),
            existing_nullable=column not in {"q1", "q3", "iqr", "limite_inferior", "limite_superior", "valor"},
        )


def downgrade() -> None:
    columns = (
        ("raw_secop", "precio_base"),
        ("raw_secop", "valor_total_adjudicacion"),
        ("contratos_procesados", "valor_total_normalizado"),
        ("contratos_procesados", "precio_base_normalizado"),
        ("contrato_outlier", "valor"),
        ("contrato_outlier", "q1"),
        ("contrato_outlier", "q3"),
        ("contrato_outlier", "iqr"),
        ("contrato_outlier", "limite_inferior"),
        ("contrato_outlier", "limite_superior"),
    )
    connection = op.get_bind()
    for table, column in columns:
        has_large_amount = connection.execute(sa.text(
            f"SELECT EXISTS (SELECT 1 FROM {table} "
            f"WHERE {column} <= -1000000000000000000 "
            f"OR {column} >= 1000000000000000000)"
        )).scalar_one()
        if has_large_amount:
            raise RuntimeError(
                f"Cannot narrow {table}.{column}: values exceed Numeric(20, 2)"
            )

    for table, column in columns:
        op.alter_column(
            table,
            column,
            existing_type=sa.Numeric(precision=38, scale=2),
            type_=sa.Numeric(precision=20, scale=2),
        )
