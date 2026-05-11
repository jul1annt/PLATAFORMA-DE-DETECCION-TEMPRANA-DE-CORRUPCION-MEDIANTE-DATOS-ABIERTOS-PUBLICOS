from Backend.core import config
from core.config import settings
from shared.base_model import Base

# Importar todos los modelos para que Alembic los detecte
from modules.ingesta.model.FuenteDatos import FuenteDatos

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
target_metadata = Base.metadata