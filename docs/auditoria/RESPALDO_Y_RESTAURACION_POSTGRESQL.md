# Respaldo y restauración de PostgreSQL

Este procedimiento es una guía operativa para preparar una migración o reparación. Los comandos de ejemplo describen el flujo aprobado; la ejecución local registrada al final usó los binarios de PostgreSQL 15.19 y una copia aislada del clúster recuperado.

## Requisitos de seguridad

- Usa una versión de `pg_dump`/`pg_restore` compatible con la versión mayor de PostgreSQL del origen.
- Configura perfiles libpq (`%APPDATA%\\postgresql\\.pg_service.conf`) llamados, por ejemplo, `app-backup-source` y `app-isolated-restore`. Guarda contraseña en `.pgpass` con ACL restrictiva o usa el gestor de secretos aprobado; no escribas credenciales en comandos, historial, logs ni este archivo.
- El perfil de restauración debe apuntar a una base aislada y vacía, nunca al origen ni a producción. Confirma host, puerto y nombre de base con el operador antes de conectar.
- Protege y cifra el archivo de respaldo en almacenamiento restringido. Puede contener datos personales y ciphertexts históricos de API keys.

## Crear el respaldo

En PowerShell, define la ruta aprobada del archivo y selecciona el perfil de solo lectura del origen. El nombre del perfil no contiene credenciales:

```powershell
$dumpPath = 'D:\backups\plataforma-2026-09-26.dump'
$env:PGSERVICE = 'app-backup-source'
pg_dump --format=custom --no-owner --no-privileges --file="$dumpPath" --dbname="service=$env:PGSERVICE"
if ($LASTEXITCODE -ne 0) { throw 'pg_dump falló; no continúes con migraciones' }
pg_restore --list "$dumpPath" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo leer el índice del respaldo' }
Get-FileHash -Algorithm SHA256 "$dumpPath"
```

Registra de forma protegida operador, fecha UTC, identidad del servicio de origen, versión mayor de PostgreSQL, tamaño y SHA-256. No incluyas contraseña ni DSN secreto. `pg_restore --list` confirma que el archivo se puede leer, pero no demuestra restaurabilidad.

## Restaurar y probar

El perfil `app-isolated-restore` debe señalar una base nueva, vacía, aislada y con permisos de creación de esquema. Confirma el destino antes de la orden siguiente:

```powershell
$env:PGSERVICE = 'app-isolated-restore'
pg_restore --exit-on-error --no-owner --no-privileges --dbname="service=$env:PGSERVICE" "$dumpPath"
if ($LASTEXITCODE -ne 0) { throw 'La restauración falló; conserva el log protegido y no uses el respaldo para reparar datos' }
```

Comprueba en esa copia la revisión Alembic y compara conteos antes de aprobar el respaldo:

```sql
SELECT version_num FROM alembic_version;

SELECT f.id, f.nombre,
       (SELECT count(*) FROM raw_secop r WHERE r.fuente_id = f.id) AS filas_crudas,
       (SELECT count(*) FROM contratos_procesados cp
        JOIN raw_secop r ON r.id = cp.raw_secop_id WHERE r.fuente_id = f.id) AS contratos_procesados,
       (SELECT count(*) FROM contrato_anomalo_incompleto a
        JOIN raw_secop r ON r.id = a.raw_secop_id WHERE r.fuente_id = f.id) AS anomalias_activas,
       (SELECT count(*) FROM sincronizacion_historial s WHERE s.fuente_id = f.id) AS sincronizaciones
FROM fuentes_datos f
ORDER BY f.id;

SELECT estado, count(*)
FROM sincronizacion_historial
GROUP BY estado
ORDER BY estado;
```

Compara los resultados con el manifiesto de conteos preparado para el mismo respaldo. Investiga toda diferencia; no interpretes ausencia de errores en `pg_restore` como prueba de consistencia lógica. Registra tiempos, resultado, versión y destino aislado. Conserva el respaldo conforme a retención y protección de datos.

## Antes de una reparación o migración

1. Identifica de forma independiente servidor, puerto, base, entorno y revisión actual. Rechaza un destino que no pueda confirmarse.
2. Crea el respaldo, calcula su hash y completa una restauración de ensayo.
3. Guarda el manifiesto de conteos por fuente/estado y el plan de reversión.
4. Ensaya la migración o reparación solo en la copia restaurada. Compara conteos, integridad referencial y comportamiento funcional.
5. Solicita la aprobación operativa correspondiente antes de repetir el procedimiento en el destino real. Mantén respaldos y claves anteriores fuera del alcance del proceso de limpieza hasta validar su política de retención.

## Ejecución local registrada — 2026-09-29

- Se encontró el clúster PostgreSQL 15 anterior en `C:\Program Files\PostgreSQL\15\data`. Se apagó limpiamente, se verificó su identificador de sistema y se conservó sin cambios. Para inspeccionarlo se creó una copia física independiente, enlazada únicamente a `127.0.0.1:5433`.
- Desde esa copia se generó el dump custom `plataformaanticorrupcion-20260929.dump`, de 5 954 588 bytes, SHA-256 `234435A9108D61B3B4167EB8C5AE97B9E476C91D2AF9DF588DF4B4645001B5E3`. `pg_restore --list` pudo leer su manifiesto y se completó una restauración aislada.
- La restauración de ensayo se migró desde `8c4b1e9d20af` hasta `c7e3a91b5d24`. Antes de reparar tenía 2 fuentes, 18 980 filas crudas, 18 354 procesadas y 2 anomalías activas. El backfill de NIT creó 1 436 valores canónicos; la reconciliación archivó 2 anomalías retiradas y terminó con cero activas. Se reprocesaron las 626 filas faltantes, quedando 18 980 crudas y procesadas.
- Se cifraron las dos API keys activas en la copia y se verificó que ambas se podían descifrar con la clave vigente y que no quedaban claves en texto claro en sus columnas activas. La rotación de las credenciales del proveedor no se ejecutó: no se observó una exposición externa. La retención del dump original y del clúster preservado sigue sujeta a la política del responsable de los datos.
- Después se generó el respaldo reparado `plataformaanticorrupcion-repaired-20260929.dump`, de 6 381 761 bytes, SHA-256 `F257CC1717481C99ED9FE7D7E2D67EE9255EBD2137DFF1C370AFAB0F68EC8162`, con 210 entradas en el manifiesto. Se restauró en la base de aplicación `127.0.0.1:5432/plataformaanticorrupcion` y se comprobaron migración, conteos por fuente, cero anomalías activas y respuesta HTTP de endpoints principales.
- Los respaldos se encuentran bajo `%LOCALAPPDATA%\PostgreSQL\15\backups`. Contienen datos de contratos; el dump original también conserva la representación previa de credenciales. Restringe acceso y aplica cifrado/retención de acuerdo con la política de datos del proyecto.
- Los tres archivos de respaldo/manifiesto se cifraron con EFS del perfil Windows actual. `cipher /c` identifica como descifrador a `DESKTOP-9LVTM1S\Julianxxo`; el directorio quedó marcado para cifrar archivos nuevos. Se verificó que el SHA-256 lógico de ambos dumps no cambiara y que `pg_restore --list` siga funcionando con ese usuario. No hay certificado EFS de recuperación configurado; antes de migrar o retirar este perfil, exporta su certificado a un almacén aprobado. La copia física antigua del clúster permanece preservada como alternativa de recuperación.
- El archivo reparado refleja la línea base recuperada de 18 980 procesos; no incluye todavía la reconciliación histórica de millones de filas que había quedado truncada por el antiguo límite de 10 000. Esa carga se está haciendo en una base de ensayo separada y no se considera finalizada hasta validar conteos, procesamiento y analítica antes de promover otro respaldo.
