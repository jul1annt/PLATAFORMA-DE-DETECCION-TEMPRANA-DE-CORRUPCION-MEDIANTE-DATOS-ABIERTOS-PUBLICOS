# Respaldo y restauración PostgreSQL

Este procedimiento se debe ejecutar y registrar sobre un entorno aislado antes de aplicar migraciones o reparar datos existentes. La restauración se hace en una base nueva y separada; nunca se restaura encima de producción.

## Requisitos y controles

- Usar `pg_dump`, `pg_restore`, `createdb` y `psql` de la misma versión mayor de PostgreSQL que el servidor.
- Confirmar el host, puerto, base de origen y responsable del cambio sin copiar contraseñas en tickets, terminales grabados o logs.
- Guardar respaldo y checksum en almacenamiento cifrado, con acceso restringido y política de retención para datos personales y credenciales de fuentes.
- Reservar un nombre de base de restauración que no exista. No usar `--clean` ni sobrescribir una restauración anterior.
- Registrar versión de PostgreSQL, fecha UTC, revisión de aplicación, revisión Alembic, nombres de las bases y conteos antes/después. No guardar contraseñas ni API keys en la evidencia.

## Capturar el respaldo

Ejecutar desde una terminal administrativa. La autenticación debe resolverse con el mecanismo aprobado del entorno (por ejemplo, `~/.pgpass` con permisos `0600`, `PGPASSFILE` protegido o el prompt del cliente); no pasar contraseñas en argumentos.

```powershell
$sourceDb = 'NOMBRE_BASE_ORIGEN'
$backupFile = 'RUTA_SEGURA\plataforma-2026-09-26.dump'
pg_dump --host HOST --port PUERTO --username USUARIO --format custom --no-owner --no-acl --file $backupFile $sourceDb
if ($LASTEXITCODE -ne 0) { throw 'pg_dump falló' }
pg_restore --list $backupFile | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'El catálogo del respaldo no se puede leer' }
Get-FileHash -Algorithm SHA256 $backupFile
```

Guardar el checksum junto al registro del cambio, separado del archivo de respaldo. Antes de migrar, registrar conteos de referencia:

```sql
SELECT fuente_id, COUNT(*) AS contratos_crudos
FROM raw_secop GROUP BY fuente_id ORDER BY fuente_id;

SELECT clasificacion_riesgo, COUNT(*) AS contratos_procesados
FROM contratos_procesados GROUP BY clasificacion_riesgo ORDER BY clasificacion_riesgo;

SELECT estado, COUNT(*) AS sincronizaciones
FROM sincronizacion_historial GROUP BY estado ORDER BY estado;
```

Si las tablas aún no existen, registrar ese hecho y el estado Alembic. Guardar los resultados con acceso restringido: incluso los conteos pueden ser información sensible.

## Restaurar en una base aislada

Crear una base nueva en una instancia de prueba accesible solo por el equipo responsable. De ser posible, usar una copia aislada con controles de red equivalentes a producción y una versión mayor compatible.

```powershell
$restoreDb = 'NOMBRE_NUEVA_BASE_TEST'
createdb --host HOST_PRUEBAS --port PUERTO_PRUEBAS --username USUARIO_PRUEBAS --template template0 $restoreDb
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear la base vacía de restauración' }
pg_restore --host HOST_PRUEBAS --port PUERTO_PRUEBAS --username USUARIO_PRUEBAS --dbname $restoreDb --no-owner --no-acl --exit-on-error $backupFile
if ($LASTEXITCODE -ne 0) { throw 'La restauración falló; conservar logs y no migrar el origen' }
```

Verificar que la restauración sea legible y coherente: repetir los conteos de referencia, comparar el checksum del archivo transferido, consultar la revisión Alembic y comprobar tablas, restricciones e índices críticos. Si la aplicación puede conectarse a esa instancia aislada, ejecutar sus comprobaciones de lectura y autenticación con credenciales de prueba. La restauración solo se considera probada cuando las comparaciones concuerdan y la base recuperada funciona.

## Después de la prueba

Anexar el archivo de evidencia sin secretos: comandos y versiones ejecutados, checksum, conteos de origen y destino, estado de Alembic, resultado de verificaciones, duración, responsable y limitaciones. Eliminar la restauración sintética o aislarla según la política del entorno. Antes de una intervención real, conservar el respaldo restaurable hasta cumplir la retención aprobada y verificar que su cifrado y permisos sigan vigentes.
