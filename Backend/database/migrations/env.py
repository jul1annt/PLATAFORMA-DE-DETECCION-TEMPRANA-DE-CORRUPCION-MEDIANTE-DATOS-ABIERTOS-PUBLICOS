import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from core.config import settings
from shared.base_model import Base
from modules.ingesta.model.FuenteDatos import FuenteDatos
from modules.ingesta.model.RawSecop import RawSecop
from modules.ingesta.model.SincronizacionHistorial import SincronizacionHistorial
from modules.transformacion.model.ContratoProcesado import ContratoProcesado
from modules.transformacion.model.ContratoAnomaloIncompleto import ContratoAnomaloIncompleto
from modules.transformacion.model.EstadisticaCamposFaltantes import EstadisticaCamposFaltantes
from modules.transformacion.model.ProcesamientoLog import ProcesamientoLog
from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo
from modules.analitica.model.proveedor_adjudicacion_directa import ProveedorAdjudicacionDirecta
from modules.analitica.model.peso_anomalia import PesoAnomalia
from modules.analitica.model.riesgo_proveedor import RiesgoProveedor
from modules.auth.model.Admin import Admin


# Alembic Config object
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()