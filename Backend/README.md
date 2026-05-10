# Backend - Plataforma de Detección Temprana de Corrupción

Este es el backend de la plataforma, construido como un monolito modular utilizando **FastAPI** (Python), **SQLAlchemy** (asíncrono) y un **Event Bus** interno.

> **Importante:** Debido a las limitaciones de longitud de rutas en Windows (Long Paths), este proyecto debe ejecutarse desde una ruta corta como `C:\DeteccionCorrupcion`.

## Requisitos Previos
- Python 3.10+
- Entorno virtual configurado (`venv`)

---

## 🚀 Guía Rápida de Ejecución

Abre tu terminal (PowerShell), asegúrate de estar ubicado en la carpeta principal del backend (ej. `C:\DeteccionCorrupcion`) y sigue estos pasos:

### 1. Activar el Entorno Virtual
```powershell
.\venv\Scripts\activate
```

*(Si es la primera vez que clonas el proyecto, instala las dependencias ejecutando: `pip install -r requirements.txt`)*

### 2. Configurar Variables de Entorno
Asegúrate de tener tu archivo `.env` configurado en la raíz de la carpeta. Puedes copiar el contenido de `.env.example` y llenarlo con tu configuración local.

### 3. Crear Tablas de la Base de Datos
Para generar la base de datos de SQLite inicial, ejecuta un script de inicialización. (El archivo `init_db.py` ya crea las tablas necesarias llamando a `create_all` de forma asíncrona):

```powershell
$env:PYTHONPATH="."
python init_db.py
```

### 4. Iniciar el Servidor Local
Para arrancar el servidor con recarga automática:

```powershell
$env:PYTHONPATH="."
uvicorn main:app --reload
```

---

## 🌐 Pruebas y API Docs

Una vez que el servidor esté corriendo, puedes ver la documentación interactiva de Swagger UI y probar todos los endpoints entrando desde tu navegador a:

👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

En los logs de la terminal, verás que tanto el **Event Bus** como el **Scheduler** de sincronización inician junto con la aplicación.
