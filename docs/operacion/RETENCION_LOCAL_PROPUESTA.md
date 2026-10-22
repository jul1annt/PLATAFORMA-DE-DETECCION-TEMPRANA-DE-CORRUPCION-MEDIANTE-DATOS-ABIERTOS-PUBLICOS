# Política aprobada de conservación local

Estado: **aprobada y aplicada el 12/10/2026**. El usuario confirmó «Aprobar la política conservadora». Se preservaron originales, historial, generaciones, ocho respaldos y paquetes actuales/anteriores; se añadió checkpoint administrativo actual y se registró revisión manual el 19/10. P15 cerrado; P05 conserva pendiente la identidad anterior. [Constancia de aplicación](CONSERVACION_APROBADA_Y_EGRESO_20261012.md). El inventario fechado del 11/10 se conserva como antecedente.

## Alcance y reglas

1. Conservar todas las generaciones únicas de SECOP, sus respaldos y la base original de 18 980 filas mientras no se resuelva la identidad histórica pendiente en P05/P12. No tienen una fecha de eliminación autorizada.
2. Conservar las versiones de `raw_secop_historial` y sus respaldos durante ese mismo periodo. Una coincidencia de contenido o tupla no habilita el borrado del original ni una asignación de identidad oficial.
3. Conservar el último respaldo completo del corte publicado y su checkpoint posterior de cuentas, sesiones, fuentes, trabajos y exportaciones. El respaldo histórico por sí solo no recupera ese estado posterior.
4. Conservar los artefactos y configuración necesarios para recuperar la aplicación actualmente usada y la versión anterior verificada. No modificar la decisión de mantener los cambios en este equipo.
5. Retirar únicamente copias derivadas de ensayo cuyo trabajo haya terminado y no tengan uso actual. Cada retiro exige comprobar identidad y ruta exactas, ausencia de sesiones/procesos activos, evidencia terminal del ensayo, origen preservado y respaldo restaurable verificado. Un archivo de estado, timeout o fallo de observación no prueba que un proceso terminó.
6. Mantener un registro local de lo preservado o retirado, motivo, identidad, tamaño y evidencia. No incluir credenciales ni claves. Cualquier retiro bloqueado por la revisión automática requiere resolver ese bloqueo; esta política no autoriza eludirlo.

## Inventario comprobado por metadatos el 11/10

Los archivos siguientes existen; tamaños y fechas se leyeron sin modificar contenidos. Esta inspección **no recalculó sus SHA-256 ni repitió sus restauraciones**: las verificaciones criptográficas y de restauración se conservan en los informes históricos.

| Respaldo en `Backend/.codex-e2e-postgres` | Bytes | Decisión propuesta |
| --- | ---: | --- |
| `plataforma_cutover_final.dump` | 3 428 333 830 | Conservar |
| `plataforma_cutover_pre_backfill.dump` | 6 383 897 | Conservar |
| `plataforma_cutover_pre_full_load.dump` | 7 714 032 | Conservar |
| `plataforma_raw_secop_cutover.dump` | 2 659 255 472 | Conservar |
| `plataforma_secop_refresh_final.dump` | 3 429 788 315 | Conservar |
| `plataformaanticorrupcion-cutover.dump` | 6 382 052 | Conservar |
| `plataformaanticorrupcion-preserved-2026-10-01.dump` | 6 374 617 | Conservar |
| `secop_20261001_final.dump` | 3 434 770 306 | Conservar |

Además, `Backend/.codex-integration-postgres/publication-20261010/operational-before.dump` conserva 6 374 617 bytes del original y `control-checkpoint/control-state.dump` conserva 14 496 bytes del estado administrativo posterior. El checkpoint incluye otros archivos necesarios; no se propone eliminarlos.

## Aprobación y aplicación

La [revisión previa a la aprobación del 12/10](PENDIENTES_LOCALES_20261012.md) comprobó ocho dumps y los checkpoints existentes. La copia completa se conserva para el alcance aislado pendiente de P06; cero sesiones no demuestra falta de uso. La aplicación posterior registró la aceptación explícita y verificó los elementos preservados sin retiros ni nuevas restauraciones.

La política propuesta no descarta ninguna generación única por antigüedad. Por tanto, elegirla no requiere borrar respaldos para demostrar su aplicación. Al aprobarla, registrar la instrucción del usuario, comprobar nuevamente los elementos preservados y documentar los retiros derivados que correspondan. Mientras P05/P12 permanezcan abiertos, registrar una revisión periódica del inventario sin habilitar vencimientos automáticos.

P15 queda cerrado con la aprobación y constancia de aplicación. P05 conserva la reconciliación anterior al versionado; aprobar conservación no resuelve identidades ausentes. Los [datos de crecimiento](../auditoria/HISTORIAL_CAPACIDAD_SECOP_20261006.md) y el [inventario histórico](../auditoria/RETENCION_Y_CAPACIDAD_SECOP_20261002.md) se reutilizan para dimensionar almacenamiento.
