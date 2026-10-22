"""Store a validated, canonical supplier NIT identity key.

Revision ID: e13ad9c24780
Revises: d6e97c4b1a20
"""
from alembic import op
import sqlalchemy as sa


revision = "e13ad9c24780"
down_revision = "d6e97c4b1a20"
branch_labels = None
depends_on = None


_VALIDATOR_SQL = r"""
CREATE FUNCTION secop_nit_identity(source_value text)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    normalized text := upper(btrim(source_value));
    body text;
    dv text;
    weights integer[] := ARRAY[71, 67, 59, 53, 47, 43, 41, 37, 29, 23, 19, 17, 13, 7, 3];
    checksum integer := 0;
    remainder integer;
    expected_dv integer;
    digit_index integer;
BEGIN
    IF normalized IS NULL OR normalized = ''
       OR normalized IN ('-', 'N/A', 'N.A.', 'NA', 'NO APLICA', 'NO DEFINIDO',
                         'NONE', 'NULL', 'SIN INFORMACION', 'SIN INFORMACIÓN',
                         'SIN REGISTRO', 'SIN NIT') THEN
        RETURN NULL;
    END IF;

    IF normalized ~ '^[0-9]+$' THEN
        body := normalized;
    ELSIF normalized ~ '^[0-9]{1,3}(\.[0-9]{3})+$'
       OR normalized ~ '^[0-9]{1,3}( [0-9]{3})+$' THEN
        body := regexp_replace(normalized, '[. ]', '', 'g');
    ELSIF normalized ~ '^[0-9]{1,3}(\.[0-9]{3})+-[0-9]$'
       OR normalized ~ '^[0-9]{1,3}( [0-9]{3})+-[0-9]$'
       OR normalized ~ '^[0-9]+-[0-9]$' THEN
        body := regexp_replace(split_part(normalized, '-', 1), '[. ]', '', 'g');
        dv := split_part(normalized, '-', 2);
    ELSE
        RETURN NULL;
    END IF;

    IF length(body) < 6 OR length(body) > 15 THEN
        RETURN NULL;
    END IF;

    IF dv IS NOT NULL THEN
        FOR digit_index IN 1..length(body) LOOP
            checksum := checksum
                + substring(body FROM digit_index FOR 1)::integer
                * weights[16 - length(body) + digit_index - 1];
        END LOOP;
        remainder := checksum % 11;
        expected_dv := CASE WHEN remainder IN (0, 1) THEN remainder ELSE 11 - remainder END;
        IF dv::integer <> expected_dv THEN
            RETURN NULL;
        END IF;
    END IF;

    RETURN body;
END;
$$;
"""


def upgrade() -> None:
    op.add_column(
        "contratos_procesados",
        sa.Column("nit_proveedor_clave", sa.String(length=15), nullable=True),
    )
    op.execute(_VALIDATOR_SQL)
    op.execute(
        "UPDATE contratos_procesados "
        "SET nit_proveedor_clave = secop_nit_identity(nit_proveedor), "
        "procesado_en = now()"
    )
    op.execute("DROP FUNCTION secop_nit_identity(text)")
    op.create_index(
        "ix_contratos_procesados_nit_proveedor_clave",
        "contratos_procesados",
        ["nit_proveedor_clave"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contratos_procesados_nit_proveedor_clave",
        table_name="contratos_procesados",
    )
    op.drop_column("contratos_procesados", "nit_proveedor_clave")
