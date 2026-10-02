# Retención y capacidad SECOP: decisión pendiente

Estado: inventario, medición y limpieza puntual de restauraciones redundantes. No se ha aprobado una política de retención ni se ha eliminado ningún respaldo. Este documento prepara el cierre de P05 y P15 del plan.

## Tamaño observado

En la copia aislada de 9 249 545 filas, `raw_secop` ocupaba 10 584 956 928 bytes de tabla (9,86 GiB) y 12 317 376 512 bytes con índices y almacenamiento asociado (11,47 GiB). Son unos 1 144 bytes de tabla por fila. `raw_secop_historial` estaba vacío y ocupaba 32 768 bytes con su estructura. Estos datos no miden todavía el crecimiento real del historial por actualizaciones; si un reemplazo archivara una versión de cada fila con contenido similar, solo las filas históricas podrían requerir del orden de 9,86 GiB adicionales antes de índices, metadatos y copias de seguridad. Es una proyección de capacidad, no un tamaño garantizado.

Los siete dumps de ensayo y preservación en `Backend/.codex-e2e-postgres` sumaban **8,89 GiB** al corte. Este total no incluye bases restauradas, clústeres PostgreSQL, archivos WAL, el futuro dump de 9 249 545 filas ni copias fuera de esa carpeta.

| Respaldo | Tamaño aproximado |
| --- | ---: |
| `plataforma_cutover_final.dump` | 3,19 GiB |
| `plataforma_raw_secop_cutover.dump` | 2,48 GiB |
| `plataforma_secop_refresh_final.dump` | 3,19 GiB |
| Cuatro dumps pequeños del corte previo, preparación y base operativa | 0,03 GiB en total |

Durante la reconstrucción de índices del corte nuevo había aproximadamente 95,8 GiB libres en la unidad. El vigilante de respaldo comprueba espacio antes de crear el dump y una restauración independiente; esa reserva temporal es necesaria además de cualquier política de conservación.

## Espacio recuperado el 2026-10-02

Se eliminaron **solo dos bases restauradas de comprobación** del clúster aislado `:5433`, cuya ruta de datos se comprobó como `recovery-clone-20260929`. Ambas tenían cero conexiones activas. Sus manifiestos registran restauración completa, 196 entradas de archivo, tamaño y SHA-256 del dump, igualdad de conteos, revisión, trabajos e índices. Antes de eliminarlas se comprobó que sus dumps y bases fuente seguían presentes.

| Restauración eliminada | Fuente y dump conservados | Tamaño de la restauración en el manifiesto |
| --- | --- | ---: |
| `plataforma_cutover_restore_final` | `plataforma_cutover_test`, `plataforma_cutover_final.dump` | 22 401 039 719 bytes |
| `plataforma_secop_refresh_restore_final` | `plataforma_secop_refresh_test`, `plataforma_secop_refresh_final.dump` | 22 412 582 247 bytes |

Los tamaños de los manifiestos suman **41,73 GiB**. El espacio libre observado en C: pasó de **90,61 GiB** antes de la limpieza a aproximadamente **134,11 GiB** después; la diferencia incluye otras escrituras y liberaciones simultáneas de la analítica en curso, por lo que no se atribuye íntegra a estas dos eliminaciones. La consulta posterior confirmó ausentes las dos restauraciones y presentes las dos fuentes, `plataforma_cutover_restore_check` para el linaje legado y `plataforma_secop_refresh_20261001_test` para el corte nuevo. La base operativa `:5432` y los siete dumps se conservaron. Esta limpieza de copias derivadas no define la retención de generaciones únicas ni cierra P05 o P15.

## Decisiones para el responsable de datos

1. Definir cuánto tiempo conservar la base y los respaldos anteriores a la reparación mientras P12 mantiene 3 405 filas sin coincidencia exacta y 157 tuplas ambiguas. Sin una identidad Socrata antigua demostrable, eliminar el original impediría revisar esas diferencias.
2. Definir cuántas generaciones completas de SECOP y cuántas versiones en `raw_secop_historial` se conservarán, y si un reemplazo total debe archivarse como dump separado en vez de copiar millones de filas al historial transaccional.
3. Definir la ubicación y capacidad del almacenamiento de largo plazo, quién valida una restauración y quién autoriza la eliminación. El disco de trabajo no equivale a un archivo permanente.
4. Definir el criterio de eliminación: generación identificada, respaldo con SHA-256 y restauración independiente verificada, plazo aprobado cumplido, dependencias de linaje resueltas y constancia de aprobación.

Hasta recibir esas decisiones, el procedimiento conserva los respaldos y no ejecuta limpieza automática de generaciones únicas. El inventario se actualizará al terminar el dump y la restauración del corte nuevo.
