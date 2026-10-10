# Despliegue coordinado y reversa

Guía de ejecución para preparar el despliegue backend/frontend. El 2026-10-06 se ejecutó en la integración persistente de este equipo, autorizado por el usuario: despliegue, reversa de aplicación, recuperación del estado local y cliente real. [La evidencia](INTEGRACION_LOCAL_20261006.md) delimita el corte histórico y los checkpoints comprobados. La publicación histórica en la base operativa se comprobó el 2026-10-10 UTC; el egreso de infraestructura sigue pendiente. [La publicación](PUBLICACION_CORTE_HISTORICO_20261010.md) fija corte, rol, OID y checkpoints. Completa la ficha y ensaya cualquier otro destino antes de programar su cambio.

## Ficha del cambio

Registrar en la orden de cambio:

- Entorno y ventana de mantenimiento:
- Responsable de aplicación y responsable de base de datos:
- Host, puerto, base, revisión Alembic actual y destino de respaldo:
- Revisión Alembic objetivo: obtenerla de `alembic heads` en el artefacto que se desplegará (la revisión aplicada a integración el 2026-10-06 UTC es `f4826b9d1c30`; el origen histórico conserva `d2804c8b39a1`; confirmar nuevamente al preparar el cambio):
- Versión/identificador de los artefactos backend, worker y frontend:
- `VITE_API_URL` que se incorporará al bundle:
- Resultado y ubicación restringida del ensayo de restauración:
- Condición de abortar y persona con autoridad para continuar:

No rellenar credenciales en la ficha. Obtener los secretos en cada proceso desde el gestor aprobado. Detener el cambio si la identidad del destino no coincide exactamente con el servidor y base autorizados.

## Preparación obligatoria

1. Revisar el diff completo y confirmar que el artefacto backend y worker corresponde a la misma revisión.
2. Ejecutar instalación limpia, auditoría de dependencias, suite local, lint, pruebas frontend, build externo, OpenAPI y matriz de acceso. Adjuntar los resultados del CI de esa misma revisión; la configuración de un workflow por sí sola no demuestra que corrió.
3. Crear respaldo PostgreSQL y completar restauración de ensayo siguiendo `RESPALDO_Y_RESTAURACION_POSTGRESQL.md`. Registrar conteos por fuente/estado de esa copia.
4. Ejecutar sobre la copia restaurada las migraciones, las pruebas PostgreSQL, las reparaciones/reconciliación previstas y los smoke tests. Medir duración, bloqueos, espacio adicional y resultados antes/después.
5. Confirmar plan de pausa/reanudación de scheduler, worker e ingestas y verificar dónde persistirán trabajos en cola.
6. Para rotación de API keys, seguir la ventana de compatibilidad descrita en `Backend/README.md`; mantener la clave anterior accesible hasta comprobar que la rotación terminó.

### Rol PostgreSQL de la aplicación

En PostgreSQL 15 o posterior, `public` puede no conceder `CREATE` por defecto. Antes de ejecutar Alembic, el DBA debe conceder `CREATE` sobre ese esquema al rol de conexión de la aplicación/migraciones (`GRANT CREATE ON SCHEMA public TO nombre_del_rol;`). Ese rol no necesita `SUPERUSER`, `CREATEDB` ni `CREATEROLE`. Verificar la conexión y la revisión Alembic con el rol de aplicación antes de continuar.

## Secuencia de despliegue

1. **Congelar escrituras:** pausar scheduler y nuevas ingestas/reprocesamientos; dejar terminar o registrar los trabajos activos. Anotar el estado de la cola y el último cursor confirmado.
2. **Proteger datos:** volver a verificar identidad del destino, respaldo restaurable y revisión Alembic. No reutilizar una sesión cuya conexión no se pueda identificar.
3. **Expandir esquema:** aplicar solo migraciones ensayadas y compatibles con la versión de aplicación que sigue corriendo. Registrar revisión inicial/final, duración, conteos y errores.
4. **Desplegar backend y worker:** usar artefactos de la misma revisión. Iniciar worker dedicado una vez que la API y el esquema sean compatibles; verificar locks, consumo de cola, logs sin secretos y salud de endpoints.
5. **Publicar frontend:** construir con el `VITE_API_URL` aprobado y servir el bundle probado. Confirmar login, ruta administrativa y manejo de sesión con una cuenta de prueba autorizada.
6. **Validar:** ejecutar smoke tests de autenticación, gestión de fuente, trabajo asíncrono, búsqueda, dashboard y exportación. Comparar resultados/errores con los umbrales aprobados.
7. **Reanudar escrituras:** solo después de validar API y worker, reanudar scheduler e ingestas. Vigilar la cola, cursores, fallos y espacio del historial de cambios SECOP.

Para cambios incompatibles, separar en despliegues de **expansión → migración de datos → retirada**. No publicar un cliente que dependa de una ruta o DTO hasta que el backend desplegado lo soporte.

## Decisión de reversa

- Si falla antes de modificar datos, detener el despliegue y volver a los artefactos previos; mantener scheduler y escrituras pausados hasta confirmar compatibilidad.
- Si solo cambió la aplicación y el esquema sigue siendo compatible, volver a la versión previa de backend/worker/frontend, comprobar que procesa la cola existente y luego reanudar trabajos.
- No ejecutar `alembic downgrade` por rutina. Revisar el cuerpo de cada migración: borrados, proyecciones limpiadas, backfills o pérdida de historia pueden ser irreversibles aunque exista una función `downgrade()`.
- Si el esquema o los datos ya cambiaron y no existe reversa ensayada, mantener el servicio en pausa. Recuperar la copia aislada aprobada o restaurar el respaldo mediante un plan de recuperación con reconciliación de escrituras posteriores. Nunca restaurar sobre una base cuyo destino no haya sido verificado.
- Después de restaurar, revalidar autenticación, conteos, integridad, trabajos/cursor y exportaciones antes de reabrir escrituras.

En la integración local, el respaldo completo histórico se complementa con el checkpoint posterior de cuentas, sesiones, fuentes, trabajos, configuración y archivos exportados. Reponer el estado por claves con los servicios pausados, conservar las referencias a fuente y administrador y alinear las secuencias. No truncar padres con `CASCADE` ni descartar filas posteriores al checkpoint sin reconciliarlas. Una restauración del dump histórico por sí sola omite el estado local nuevo. La reposición ensayada restauró las huellas de las cuatro tablas de control y un acceso desactivado, conservando los contratos; la restauración completa de la capa histórica se acredita con el ensayo independiente del 03/10.

## Cierre de cambio

Guardar en el registro del cambio los hashes de los artefactos y respaldo, revisiones Alembic, resultados CI, conteos antes/después, smoke tests, incidentes, decisiones de reversa y aprobaciones. Mantener logs, dumps y claves dentro de controles de acceso/retención del entorno.

## Publicación histórica en este equipo — 2026-10-10 UTC

Destino canónico: `plataformaanticorrupcion:5432`, OID 24577; original conservado: `plataformaanticorrupcion_pre_20261010`, OID 17930. Backend/worker `915e863`, revisión `f4826b9d1c30`, frontend `9362d94`. La integración anterior :5433 conserva su propio estado. El corte del 01/10/2026 tiene fecha visible y fuentes pausadas.

El directorio privado `publication-20261010/control-checkpoint/` conserva configuración anterior, exportaciones y dump de las cuatro tablas de control inmediatamente antes de promoción. Una reversa exige servicios detenidos, cero trabajos activos y conexiones, identidades/OID cotejados y reconciliación de cualquier escritura nueva antes de volver a apuntar a la integración anterior. El original de 18 980 filas se conserva para linaje; no sustituye el corte publicado.

Para recuperar el histórico desde su dump, crear una nueva base UTF8 con locale `Spanish_Argentina.1252` desde el comienzo, aplicar las dos migraciones aditivas y preparar estadísticas. Si el locale por defecto difiere, [el SQL de recuperación](../operacion/PRESERVAR_LOCALE_SECOP_20261001.sql) conserva explícitamente las comparaciones de sus 102 columnas: exige rol ordinario, base/OID, puerto y revisión, y rechaza reescribir los heaps. Combinar el respaldo histórico con el checkpoint posterior por claves y verificar huellas, secuencias y archivos. No iniciar otra carga o normalización completa para este corte.
