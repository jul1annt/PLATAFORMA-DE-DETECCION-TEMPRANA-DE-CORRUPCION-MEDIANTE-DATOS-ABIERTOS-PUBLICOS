# ⚙️ Backend - API & Motor de Procesamiento

El backend de la **Plataforma de Detección Temprana de Corrupción** es una API REST robusta construida con **FastAPI**. Se encarga de gestionar la base de datos PostgreSQL, ejecutar de manera programada o manual la ingesta y limpieza de datos, realizar el análisis de riesgos y exponer los endpoints consumidos por el cliente web de manera segura.

---

## 🛠️ Tecnologías y Librerías Principales

* **FastAPI:** Framework web moderno y de alto rendimiento.
* **SQLAlchemy 2.0:** Mapeador objeto-relacional (ORM) para la interacción con PostgreSQL.
* **Alembic:** Herramienta para el control de versiones y migraciones de la base de datos.
* **APScheduler:** Programador de tareas en segundo plano para la automatización de la ingesta de datos.
* **Fernet (Cryptography):** Cifrado simétrico para el almacenamiento seguro de datos sensibles.
* **PyJWT & Passlib:** Mecanismos de seguridad para autenticación con tokens JWT y hashing de contraseñas.

---

## 📂 Módulos de la Aplicación (`Backend/modules/`)

* **`auth`:** Registro, login de administradores y generación de tokens JWT de sesión.
* **`ingesta`:** Registro de fuentes de datos, validación de conexión y triggers para descargas manuales/automáticas de datos abiertos.
* **`transformacion`:** Motor de limpieza de datos crudos, auditoría de calidad y reporteo de anomalías en las fuentes.
* **`analitica`:** Detección de banderas rojas, cálculo de indicadores agregados y administración de contratos sospechosos.
* **`visualizacion`:** Generación de métricas y datos estructurados optimizados para tableros de información (públicos y administrativos).

---

## 📋 Requisitos Previos

Antes de comenzar, asegúrate de tener instalado:

* [Python 3.10](https://www.python.org/downloads/) o superior.
* [PostgreSQL](https://www.postgresql.org/download/) en ejecución local o remota.
* `pip` (Administrador de paquetes de Python).

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

* **En Linux / macOS:**
  ```bash
  python -m venv venv
  source venv/bin/activate
  ```
* **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
* **En Windows (Command Prompt - CMD):**
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```

### 3. Instalar Dependencias

Una vez activado el entorno virtual, instala todos los paquetes requeridos:

```bash
pip install -r requirements-dev.txt
```

`requirements.in` y `requirements-dev.in` son los archivos fuente; los archivos `.lock` fijan versiones y hashes. Para actualizar un paquete, edita el `.in` correspondiente y regenera ambos locks con `pip-compile --generate-hashes --strip-extras --allow-unsafe --output-file requirements.lock requirements.in` y `pip-compile --generate-hashes --strip-extras --allow-unsafe --output-file requirements-dev.lock requirements-dev.in`.

### 4. Configurar Variables de Entorno

Copia el archivo de plantilla `.env.example` y renómbralo a `.env`:

```bash
cp .env.example .env
```

Abre `.env` en tu editor de texto y completa los valores necesarios:

* Configura las credenciales de tu base de datos PostgreSQL (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`).
* En PostgreSQL 15 o posterior, concede al rol de conexión permiso para crear objetos en `public` antes de aplicar Alembic. El rol no requiere superusuario:
  ```sql
  GRANT CREATE ON SCHEMA public TO nombre_del_rol;
  ```

  Ejecuta esto con el rol administrador de la base y luego usa el rol de conexión de la aplicación/migraciones. CI aplica el mismo permiso y comprueba las migraciones con un rol sin privilegios de superusuario.
* Genera una clave de cifrado simétrico segura (Fernet) para la variable `ENCRYPTION_KEY`. Puedes generar una ejecutando el siguiente comando:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
* Establece una frase secreta robusta para `SECRET_KEY` (usada para firmar los JWT).
* Ajusta tu zona horaria local en `SCHEDULER_TIMEZONE` (ej: `America/Bogota`).
* `LOGIN_MAX_ATTEMPTS` y `LOGIN_WINDOW_MINUTES` limitan los fallos por usuario/IP; PostgreSQL coordina las solicitudes concurrentes para esa clave mediante un bloqueo transaccional. `INGESTA_OVERLAP_HOURS` determina cuánto se vuelve a consultar desde la última sincronización exitosa (48 horas por defecto) para incorporar actualizaciones tardías; `INGESTA_MAX_RECORDS_PER_SYNC` fija el máximo de filas por trabajo (100 000 por defecto).
* Configura `EXPORT_ARTIFACT_DIR` como directorio escribible y compartido por todos los procesos API y el worker. `EXPORT_MAX_ROWS` limita los contratos por exportación (50 000 por defecto; PDF conserva el máximo de 1 000). Los enlaces de exportación vencen según `EXPORT_CAPABILITY_TTL_HOURS`; los artefactos antiguos se eliminan según `EXPORT_ARTIFACT_TTL_HOURS`.

### CORS y sesión administrativa

`CORS_ORIGINS` es una lista separada por comas de orígenes HTTP(S) exactos, incluidos esquema y puerto cuando aplique, por ejemplo `https://portal.example.gov.co,https://admin.example.gov.co`. No admite comodines, rutas ni credenciales dentro de la URL. En producción usa HTTPS. CORS solo permite los métodos y encabezados que consume la aplicación; no habilita cookies entre orígenes.

El cliente envía el JWT como `Authorization: Bearer ...`. Cada token identifica una sesión persistida y revocable en PostgreSQL; `/api/auth/logout` revoca la sesión actual y las rutas administrativas vuelven a comprobar que el administrador siga activo.

### Rotar claves de API de fuentes

La aplicación cifra las claves nuevas con `ENCRYPTION_KEY`. Para cambiarla sin dejar claves temporalmente ilegibles, actualiza primero el código que acepta `ENCRYPTION_KEY_PREVIOUS` manteniendo todavía activa la clave actual. Antes de cambiar la clave activa, drena y detén todas las versiones antiguas del API y worker; reinicia todos los procesos con la clave nueva y la anterior configuradas, y reanuda tráfico/escrituras solo cuando todo el conjunto lea ambas. Durante esa ventana la aplicación puede abrir ciphertexts de ambas claves y cifra valores nuevos con la activa. Haz primero una copia de la base y verifica que puedes restaurarla en un entorno aislado.

Desde `Backend`, inyecta `ENCRYPTION_KEY_OLD` desde el gestor de secretos aprobado solo en el proceso operador/comando, sin escribir su valor en el historial del shell. El comando informa cantidades sin imprimir credenciales; por defecto no escribe:

```powershell
# ENCRYPTION_KEY_OLD debe estar disponible en el entorno del proceso
python scripts/rotate_source_keys.py
python scripts/rotate_source_keys.py --apply
```

Ejecuta primero el diagnóstico y la aplicación sobre una copia aislada. `--apply` calcula todas las sustituciones antes de modificarlas y confirma los cambios en una transacción; si falla el descifrado, revierte. Se puede repetir después de una interrupción. Verifica el conteo actualizado y prueba en el entorno aislado que todas las fuentes se pueden descifrar. Solo cuando todas las réplicas estén actualizadas y no haya valores con la clave anterior, elimina `ENCRYPTION_KEY_PREVIOUS` del despliegue. Conserva o elimina de forma controlada las claves antiguas en respaldos conforme a la política de retención; no las escribas en comandos registrados ni logs.

Las contraseñas nuevas de administrador deben tener entre 12 y 128 caracteres y no pueden consistir solo en espacios ni contener caracteres de control. Los espacios que sí formen parte de una frase se conservan literalmente. El login acepta de 8 a 128 caracteres para permitir cuentas heredadas, pero tampoco recorta ni normaliza la contraseña. El límite de intentos de login se aplica por usuario/IP y responde `429` al superar el máximo.

## Contrato OpenAPI

FastAPI publica el contrato en `/openapi.json`; la copia versionada está en `Backend/openapi.json`. Después de cambiar rutas o DTOs, actualiza y comprueba la copia con:

```bash
python scripts/export_openapi.py
python scripts/export_openapi.py --check
```

El generador importa la aplicación para construir el esquema estático y no abre una conexión a PostgreSQL. Los tipos TypeScript derivados se generan desde esa copia; las instrucciones están en `frontend/README.md`.

---

## 🗄️ Inicialización de la Base de Datos (Migraciones)

El backend utiliza **Alembic** para administrar el esquema. Conserva el historial de migraciones y aplica las revisiones existentes:

```bash
alembic upgrade head
```

Antes de migrar una base con datos existentes, crea y verifica un respaldo restaurable. Después de aplicar las migraciones, aprovisiona el primer administrador desde una terminal confiable:

```bash
python scripts/create_first_admin.py --username admin --email admin@example.com
```

En producción, ejecuta el worker separado de los procesos HTTP. Las solicitudes de sincronización y reprocesamiento crean trabajos persistidos y responden `202 Accepted` con su identificador; consulta `GET /api/jobs/{id}` para ver el estado y el resultado. El worker atiende la cola, mientras que el scheduler encola las sincronizaciones vencidas. Si una ingesta llega a su límite, el historial queda `PARCIAL`; cada cursor se confirma en la misma transacción que su lote y el siguiente trabajo retoma la ventana desde ese punto:

```bash
python worker.py
```

La fuente oficial SECOP II puede sustituir todos sus IDs Socrata en una actualización. Antes de una ventana de ingesta, el servicio coteja una muestra de IDs locales con una firma global de la fuente, incluso si el watermark es posterior a `:updated_at`. Durante una carga larga vuelve a comprobar la muestra cada 100 000 filas y la firma cada millón, además de una comprobación final antes de avanzar el watermark. Si el resultado del trabajo incluye `replacement_detected`, `source_changed` o `identity_unverifiable`, la ventana termina `PARCIAL` sin cursor reanudable y la fuente queda inactiva para el programador. Conserva respaldo y datos previos, y prepara una carga completa en una base aislada. Reactiva la fuente solamente después de cotejar y promover el corte correcto; no repitas la misma ventana ni borres filas operativas para resolver ese estado. `scripts/probe_secop_generation.py` permite consultar la firma y la muestra sin escribir datos; `scripts/verify_secop_coverage.py` coteja el corte aislado con la fuente antes de promoverlo.

Las exportaciones de contratos se generan en segundo plano. El endpoint devuelve un token de capacidad que debe enviarse en `X-Export-Token` al consultar el estado y descargar. El token no se incluye en las URLs y caduca; la tarea programada limpia archivos por edad. En despliegues con API y worker en máquinas o contenedores distintos, monta el mismo almacenamiento compartido en `EXPORT_ARTIFACT_DIR` para todos ellos.

Configura `INGESTA_ALLOWED_HOSTS` solo con hosts de proveedores de confianza y limita la salida de red del worker para que no alcance redes privadas ni servicios de metadatos. La aplicación también valida protocolo, puerto, host, ruta y redirecciones. Los trabajos activos se deduplican por recurso, se reclaman con bloqueos PostgreSQL entre procesos y vuelven a la cola si el worker cae y pierde su bloqueo.

Cuando un upsert de SECOP cambia un proceso existente, PostgreSQL guarda la fila anterior en `raw_secop_historial` dentro de la misma transacción; una relectura idéntica no crea otra versión. El historial empieza a partir de aplicar la migración `c7e3a91b5d24`, no reconstruye cambios previos, y su crecimiento debe vigilarse al dimensionar almacenamiento y definir retención.

Las pruebas usan PostgreSQL desechable en CI. No uses una base con datos reales para validar migraciones; prepara un entorno aislado y demuestra que el respaldo se puede restaurar.

### Reconciliar anomalías vigentes

Desde `Backend`, el comando de reconciliación compara anomalías activas con la detección actual. Sin opciones aplica solo diagnóstico; informa diferencias y conteos antes/después sin escribir datos:

```bash
python scripts/reconcile_transformation.py --batch-size 500
```

Para reparar, especifica un archivo de checkpoint nuevo. El comando conserva el historial de anomalías retiradas, confirma cada lote y reconstruye al final las estadísticas de campos faltantes. Si se interrumpe, reanuda con el mismo destino y checkpoint:

```bash
python scripts/reconcile_transformation.py --apply --batch-size 500 --checkpoint var/reconcile-transformacion.json
python scripts/reconcile_transformation.py --apply --resume --checkpoint var/reconcile-transformacion.json
```

El checkpoint identifica host, puerto y nombre de base (nunca credenciales), versión de reglas, corte y último ID confirmado. Para una reparación, apunta `DATABASE_URL` a PostgreSQL aislado y respalda/verifica la restauración antes de ejecutarla.

---

## ⚡ Ejecución del Servidor de Desarrollo

Una vez configurada la base de datos, inicia el servidor de desarrollo FastAPI usando **Uvicorn**:

```bash
uvicorn main:app --reload --port 8000
```

* El servidor se levantará en: [http://localhost:8000](http://localhost:8000)
* **Documentación Interactiva de la API:**
  * **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs) (Permite probar todos los endpoints en vivo)
  * **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
