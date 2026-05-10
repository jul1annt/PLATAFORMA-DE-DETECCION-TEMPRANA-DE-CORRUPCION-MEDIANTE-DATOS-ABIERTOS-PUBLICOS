# Backend - Plataforma de Detección Temprana de Corrupción

Este es el backend de la plataforma, construido como un monolito modular utilizando **FastAPI** (Python), **SQLAlchemy** (asíncrono) y un **Event Bus** interno.

## Requisitos Previos
- Python 3.10+
- Entorno virtual configurado (`venv`)

---

## 🚀 Guía Rápida de Ejecución (Windows)

Sigue estos pasos desde una terminal (PowerShell) estando ubicado en la carpeta `Backend`:

### 1. Activar el Entorno Virtual
```powershell
.\venv\Scripts\activate
```

*(Si no has instalado las dependencias, ejecuta: `pip install -r requirements.txt`)*

### 2. Configurar Variables de Entorno
Asegúrate de tener tu archivo `.env` configurado en la raíz de la carpeta `Backend`. Puedes copiar el contenido de `.env.example` y llenarlo con tu configuración local.

### 3. Crear las Tablas en la Base de Datos (Workaround)
Si presentas el error de "ruta demasiado larga" (Long Paths en Windows) al intentar correr las migraciones de Alembic, puedes forzar la creación de las tablas directamente desde SQLAlchemy ejecutando:

```powershell
$env:PYTHONPATH="."
python -c "import asyncio; from core.database import engine; from modules.data_sources.models.entity import Base; asyncio.run(Base.metadata.create_all(engine))"
```

### 4. Iniciar el Servidor Local
Para correr el servidor con soporte para recarga automática en cada cambio de código:

```powershell
$env:PYTHONPATH="."
uvicorn main:app --reload
```

---

## 🌐 Pruebas y API Docs

Una vez que el servidor esté corriendo, puedes ver la documentación generada automáticamente e interactuar con todos los endpoints creados en:

👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

En los logs de la consola podrás verificar que el **Event Bus** y el **Scheduler** de sincronización de fuentes se inicializan y detienen correctamente con el ciclo de vida de la aplicación.
