# ⚙️ Backend - API & Motor de Procesamiento

El backend de la **Plataforma de Detección Temprana de Corrupción** es una API REST robusta construida con **FastAPI**. Se encarga de gestionar la base de datos PostgreSQL, ejecutar de manera programada o manual la ingesta y limpieza de datos, realizar el análisis de riesgos y exponer los endpoints consumidos por el cliente web de manera segura.

---

## 🛠️ Tecnologías y Librerías Principales
*   **FastAPI:** Framework web moderno y de alto rendimiento.
*   **SQLAlchemy 2.0:** Mapeador objeto-relacional (ORM) para la interacción con PostgreSQL.
*   **Alembic:** Herramienta para el control de versiones y migraciones de la base de datos.
*   **APScheduler:** Programador de tareas en segundo plano para la automatización de la ingesta de datos.
*   **Fernet (Cryptography):** Cifrado simétrico para el almacenamiento seguro de datos sensibles.
*   **Python-Jose & Passlib:** Mecanismos de seguridad para autenticación con tokens JWT y hashing de contraseñas.

---

## 📂 Módulos de la Aplicación (`Backend/modules/`)

*   **`auth`:** Registro, login de administradores y generación de tokens JWT de sesión.
*   **`ingesta`:** Registro de fuentes de datos, validación de conexión y triggers para descargas manuales/automáticas de datos abiertos.
*   **`transformacion`:** Motor de limpieza de datos crudos, auditoría de calidad y reporteo de anomalías en las fuentes.
*   **`analitica`:** Detección de banderas rojas, cálculo de indicadores agregados y administración de contratos sospechosos.
*   **`visualizacion`:** Generación de métricas y datos estructurados optimizados para tableros de información (públicos y administrativos).

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:
*   [Python 3.10](https://www.python.org/downloads/) o superior.
*   [PostgreSQL](https://www.postgresql.org/download/) en ejecución local o remota.
*   `pip` (Administrador de paquetes de Python).

---

## 🚀 Guía de Instalación y Configuración

Sigue estos pasos detallados para configurar el entorno de ejecución:

### 1. Clonar el repositorio y acceder al Backend
Abre una terminal y colócate en el directorio del Backend:
```bash
cd Backend
```

### 2. Crear y Activar el Entorno Virtual (`venv`)
Crea un entorno de Python aislado para evitar conflictos de librerías:

*   **En Linux / macOS:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
*   **En Windows (PowerShell):**
    ```powershell
    python -m venv venv
    .\venv\Scripts\Activate.ps1
    ```
*   **En Windows (Command Prompt - CMD):**
    ```cmd
    python -m venv venv
    .\venv\Scripts\activate.bat
    ```

### 3. Instalar Dependencias
Una vez activado el entorno virtual, instala todos los paquetes requeridos:
```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno
Copia el archivo de plantilla `.env.example` y renómbralo a `.env`:
```bash
cp .env.example .env
```
Abre `.env` en tu editor de texto y completa los valores necesarios:
*   Configura las credenciales de tu base de datos PostgreSQL (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).
*   Genera una clave de cifrado simétrico segura (Fernet) para la variable `ENCRYPTION_KEY`. Puedes generar una ejecutando el siguiente comando:
    ```bash
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
*   Establece una frase secreta robusta para `SECRET_KEY` (usada para firmar los JWT).
*   Ajusta tu zona horaria local en `SCHEDULER_TIMEZONE` (ej: `America/Bogota`).

---

## 🗄️ Inicialización de la Base de Datos (Migraciones)

El backend utiliza **Alembic** para administrar el esquema de base de datos. Para iniciar por primera vez o reestructurar el esquema:

> [!WARNING]
> Si estás en un entorno de desarrollo limpio y necesitas regenerar el esquema desde cero, asegúrate de borrar cualquier archivo de migración antiguo dentro del directorio `database/migrations/versions/` antes de ejecutar los siguientes comandos.

1.  **Generar una nueva revisión de base de datos:**
    ```bash
    alembic revision --autogenerate -m "initial"
    ```
2.  **Aplicar la migración a tu base de datos:**
    ```bash
    alembic upgrade head
    ```

---

## ⚡ Ejecución del Servidor de Desarrollo

Una vez configurada la base de datos, inicia el servidor de desarrollo FastAPI usando **Uvicorn**:

```bash
uvicorn main:app --reload --port 8000
```

*   El servidor se levantará en: [http://localhost:8000](http://localhost:8000)
*   **Documentación Interactiva de la API:**
    *   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (Permite probar todos los endpoints en vivo)
    *   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)