# Comprobación de permisos del ciclo diario

La revisión encontró que `missing_runtime_permissions` comprobaba tablas analíticas, vistas e historiales ciudadanos, pero omitía objetos utilizados por los trabajos hijos de ingesta y normalización. Un rol podría superar esa comprobación y fallar después al despachar o ejecutar la actualización diaria.

## Corrección

Se incorporan comprobaciones de solo lectura para:

| Objeto | Privilegios comprobados |
| --- | --- |
| `background_jobs` | SELECT, INSERT, UPDATE |
| `fuentes_datos` | SELECT, UPDATE |
| `raw_secop_historial` | SELECT, INSERT |
| `sincronizacion_historial` | SELECT, INSERT, UPDATE |
| Secuencias asociadas a inserciones en raw, historiales, cola y tablas normalizadas | USAGE, SELECT |

Las secuencias se resuelven con `pg_get_serial_sequence`; no se supone un nombre y las tablas sin secuencia se omiten. Se mantienen las comprobaciones previas. El comprobador no concede privilegios, no inserta registros y no habilita la publicación ni la programación.

## Verificación

Las pruebas focalizadas pasaron: 17 pruebas unitarias nuevas y una comprobación de permisos en PostgreSQL aislado, 18 en total. Cubren permisos ausentes por objeto y operación, secuencias, ausencia de secuencia y que no se exija borrar datos de estas nuevas tablas.

La batería completa del backend terminó con **691 pruebas aprobadas**, cero fallos, errores u omisiones, en 86,89 segundos. La [evidencia consolidada y los hashes](VALIDACION_PERMISOS_CICLO_DIARIO_20261019.json) identifican el código y los registros de esta ejecución. La simulación de permisos ausentes es unitaria; la comprobación con PostgreSQL acredita que el rol aislado dispone de los permisos consultados. No se revocaron permisos reales para producir los casos negativos.

## Alcance pendiente

Esto refuerza una condición del inicio; no acredita que el paquete final arranque y se recupere correctamente con modelos reales aprobados. Siguen pendientes la evidencia judicial suficiente, entrenamiento y evaluación de ambas etapas y el ensayo operativo del paquete final. La plataforma publicada conserva su configuración.
