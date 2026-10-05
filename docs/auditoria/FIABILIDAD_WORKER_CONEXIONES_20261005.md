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

Pasaron **219 pruebas** del backend tras corregir la propiedad de la conexión. Después de añadir el cierre de registros enlazados pasaron **24 pruebas focalizadas**, incluidas las cuatro nuevas comprobaciones PostgreSQL y el flujo real de aplicación. El CI de la revisión final se comprueba por separado.

## Límites

Las regresiones usan datos pequeños. El ensayo con el corte de **9 249 545** contratos, dos procesos de worker y HTTP local se registra aparte en `RECUPERACION_WORKER_CARGA_20261005.json`; mientras no termine verificado, no se presenta como recuperación completa a escala.

Este cambio conserva las confirmaciones por lote y el checkpoint de ingesta. No añade reanudación desde un checkpoint al reprocesamiento forzado: ese recorrido todavía puede repetir la lectura del universo después de una caída. Las escrituras a escala, los picos de todos los procesos y los umbrales de aceptación de despliegue siguen pendientes en P16.
