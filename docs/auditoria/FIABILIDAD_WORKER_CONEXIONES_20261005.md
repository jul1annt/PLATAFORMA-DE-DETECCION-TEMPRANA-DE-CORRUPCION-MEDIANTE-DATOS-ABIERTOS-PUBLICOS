# Conexión y recuperación de trabajos

Estado: corrección local comprobada; P16 conserva los requisitos de carga, picos y umbrales pendientes.

## Fallo reproducido

La prueba `test_worker_keeps_lock_connection_checked_out_between_commits` falló contra el código anterior: mientras el ejecutor esperaba, `recover_abandoned_jobs()` devolvió **1**, aunque el trabajo seguía vivo. Antes de comprobar ese efecto, una primera ejecución también confirmó que el grupo tenía **0** conexiones reservadas por el worker después de confirmar la reclamación.

Los bloqueos de sesión PostgreSQL quedaban en una conexión que `Session.commit()` podía devolver al grupo compartido. El recuperador podía tomar esa misma conexión y obtener de nuevo su bloqueo, interpretando el trabajo vivo como abandonado. Además, el ejecutor creaba otra sesión, por lo que perder la conexión del bloqueo no garantizaba detener sus escrituras.

## Corrección

- La reclamación, los servicios y el resultado comparten una conexión reservada hasta terminar el trabajo. Las confirmaciones por lote conservan esa conexión.
- El recuperador también mantiene su conexión hasta liberar sus bloqueos.
- Un control antes de ejecutar SQL impide continuar sobre una conexión invalidada o sustituida. Si un servicio captura el fallo y trata de reconectar, el intento antiguo sigue sin poder escribir.
- Después de perder la conexión, el worker deja la recuperación al mecanismo durable; no guarda un resultado ni un estado de error que pueda sobrescribir el del siguiente intento.
- Los nuevos registros de transformación enlazan su universo con `background_job_id`. Al recuperar ese trabajo, solo sus registros `EN_PROCESO` enlazados se cierran como `ERROR`, conservando su último avance. No se infiere el vínculo de registros históricos.

El manejo explícito de conexiones y el evento usado se apoyan en las APIs documentadas de [SQLAlchemy: conexiones](https://docs.sqlalchemy.org/en/20/core/connections.html) y [eventos antes de ejecutar SQL](https://docs.sqlalchemy.org/en/20/core/events.html#sqlalchemy.events.ConnectionEvents.before_execute).

## Evidencia local

En `codex_plan_worker_failure_test`, PostgreSQL 15 aislado en `127.0.0.1:5433`, migrado a `d2804c8b39a1`:

- La regresión verifica que un recuperador no reencola un trabajo vivo y que su conexión sigue reservada entre confirmaciones.
- Tres confirmaciones del ejecutor mantienen el mismo PID PostgreSQL y el bloqueo del trabajo.
- Una desconexión real con `pg_terminate_backend` permite recuperar el trabajo y terminar el intento 2. El intento antiguo, liberado después, no consigue ejecutar su escritura ni sobrescribir el resultado recuperado.
- La recuperación cierra solo el registro de transformación enlazado; conserva registros de otros trabajos y registros históricos sin vínculo.

Pasaron **219 pruebas** del backend tras corregir la propiedad de la conexión. Después de añadir el cierre de registros enlazados pasaron **24 pruebas focalizadas**, incluidas las cuatro nuevas comprobaciones PostgreSQL y el flujo real de aplicación. Tras añadir el recorrido vacío y memoria transaccional pasaron **222 pruebas** del backend. Los dos CI de `972bcd3` pasaron para la corrección de conexión y registros; el CI de la revisión posterior se comprueba por separado.

## Límites

Las regresiones usan datos pequeños. El ensayo con el corte de **9 249 545** contratos, dos procesos de worker y HTTP local terminó `verified_and_cleaned`, con comprobación independiente en `RECUPERACION_WORKER_CARGA_20261005.json`. El primer backend se terminó mientras ejecutaba la comparación de candidatos; el recuperador no reclamó el trabajo mientras estaba vivo y el segundo proceso lo completó en el intento 2. Hubo **4 088/4 088 HTTP 200** en rondas de ocho clientes; mediana 30,86 ms, p95 36,32 ms y máximo 515,58 ms. Los conteos, cuatro analíticas y estadísticas coinciden antes y después; solo se retiraron filas creadas para el ensayo.

Este ensayo comprobó un recorrido real de detección de pendientes sobre todo el corte, que resultó vacío: **no hubo lotes de cambios escritos**. Los procesos ya estaban cargados antes de añadir el vínculo de logs y las optimizaciones posteriores; esas adiciones se cubren en las pruebas pequeñas, sin atribuirles el tiempo de esta corrida. La memoria muestreada corresponde al proceso de API/coordinador y no a todos los procesos PostgreSQL ni al segundo worker.

Las escrituras a escala, los picos de todos los procesos y los umbrales de aceptación de despliegue siguen pendientes en P16. La reanudación del reprocesamiento forzado se añadió después del ensayo grande, con la evidencia separada descrita a continuación.

## Reanudación del reprocesamiento forzado

Los trabajos forzados nuevos guardan un checkpoint versionado en el universo del log, junto con sus contratos y anomalías, en la misma transacción de cada lote. El siguiente intento del mismo trabajo conserva el máximo de ID crudo, el número inicial de candidatos, los contadores acumulados y la fecha UTC de referencia para detectar anomalías. Retoma después del último ID confirmado sin repetir el conteo del universo. Cada intento conserva su propio log y enlaza el anterior mediante `reanudado_desde_log_id`.

Si un lote revierte, el registro de error conserva exclusivamente los contadores e ID del último lote confirmado. Si el servicio terminó pero se perdió la conexión antes del resultado del trabajo, el siguiente intento reutiliza el cierre completo del log, sin volver a transformar los contratos. Un checkpoint versionado con reglas, alcance, fecha o contadores incompatibles produce error; no se usa para omitir filas.

La consulta del log pertenece al repositorio, la validación de su contenido al dominio y la decisión de reanudar al servicio. El worker sigue siendo responsable de exclusión, propiedad de la conexión y recuperación del trabajo. No se añade dependencia de la transformación hacia el worker ni se cambia el esquema de PostgreSQL.

En `codex_plan_resume_test`, PostgreSQL 15 aislado y migrado a `d2804c8b39a1`, se ensayaron dos desconexiones reales:

| Momento de desconexión | Filas ya confirmadas | Filas normalizadas por el intento 2 | Filas confirmadas repetidas |
| --- | ---: | ---: | ---: |
| Durante el segundo lote | 1 000 | 1 005 | 0 |
| Tras completar el servicio, antes del resultado durable | 2 005 | 0 | 0 |

Ambos trabajos terminaron `EXITOSO` en el intento 2, con 2 005 contratos, 10 025 anomalías activas y cero anomalías históricas duplicadas. Solo se contó el universo una vez por trabajo. Las pruebas también comprueban que el recuperador no reclama el intento vivo y que este no sobrescribe el resultado del recuperado. Pasaron **239 pruebas backend**, sin fallos ni omisiones. `REANUDACION_REPROCESAMIENTO_20261005.json` conserva los resultados de las aserciones, contadores, cursores, tiempos y límites. La base desechable se retiró tras verificar filas de prueba ausentes y cero sesiones; la consulta de solo lectura a `:5432` confirmó 18 980 crudos y procesados.

Este ensayo usa 2 005 filas sintéticas y dos hilos de worker con conexiones PostgreSQL independientes; no mide HTTP concurrente ni escrituras sobre los nueve millones de registros. La reanudación se aplica a checkpoints nuevos de trabajos **forzados**; los logs legados sin versión no permiten inferir un avance confiable y el recorrido incremental mantiene su selección de pendientes. Los límites de ID y candidatos no congelan el contenido de `raw_secop`: cambios posteriores en filas ya evaluadas siguen correspondiendo al próximo procesamiento incremental. No se reinició ningún corte completo ni se promovió un respaldo histórico.
