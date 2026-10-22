# Crecimiento real del historial SECOP en este equipo

Fecha: 2026-10-06 UTC. Alcance: componente de medición de **P05**. El plan conserva **93/101 puntos completos y ocho pendientes**; P05 necesita todavía la reconciliación anterior al versionado y una decisión de retención.

## Resultado observado

Se archivaron **6 000 versiones** de una muestra de **2 000 registros**. El crecimiento de `raw_secop_historial`, incluidos índices y almacenamiento asociado, fue **12 730 368 bytes (12,14 MiB)**: **2 121,728 bytes por versión**, aproximadamente **2,07 KiB**. Una actualización que cambia solamente `sincronizado_en` generó **cero versiones**.

| Etapa confirmada | Versiones | Tabla principal, bytes | Índices, bytes | Relación total, bytes | Actualización y commit, segundos |
| --- | ---: | ---: | ---: | ---: | ---: |
| Estructura vacía | 0 | 0 | 24 576 | 32 768 | — |
| Solo fecha de sincronización | 0 | 0 | 24 576 | 32 768 | 0,368 |
| Primer cambio de contenido | 2 000 | 4 046 848 | 221 184 | 4 358 144 | 0,629 |
| Segundo cambio de contenido | 4 000 | 8 101 888 | 368 640 | 8 585 216 | 0,601 |
| Tercer cambio de contenido | 6 000 | 12 156 928 | 466 944 | 12 763 136 | 0,676 |

El crecimiento se calcula restando la estructura vacía al total final, no dividiendo el tamaño de la tabla cruda. `pg_total_relation_size` incluye el almacenamiento asociado; no equivale solo a la suma de las dos columnas anteriores. El promedio de `pg_column_size(datos_anteriores)` fue 1 678,318 bytes al final, con mínimo 1 412 y máximo 2 282: es el tamaño del dato almacenado, distinto del costo completo por versión. Los tiempos describen esta prueba pequeña y no acreditan rendimiento de escrituras a escala ni un SLA.

## Método y preservación

1. La integración persistente `plataforma_integracion_local`, puerto 5433 y OID 74053, siguió activa. La lectura usó su rol ordinario y una transacción de solo lectura. Revisión: `f4826b9d1c30`; artefacto desplegado: `9362d94f9dbfbdf352ae11585a2bfd44318b11e6`.
2. Se tomaron 100 anclas equidistantes entre los IDs mínimo y máximo de `raw_secop`, leyendo por índice las 20 filas siguientes a cada ancla. Tras eliminar IDs repetidos quedaron 2 000 filas. El rango original era 1–9 249 545; la muestra abarcó 1–9 157 068. Es una muestra determinista por ID, sin aleatoriedad ni estratificación por fecha.
3. Se creó únicamente `plataforma_historial_capacidad_20261006_test`, OID 74688, con el rol ordinario como propietario. Se aplicó el esquema vacío del mismo artefacto y se copiaron esas filas y su fuente inactiva, sin clave API. No se instalaron workers ni se encolaron trabajos en la base temporal.
4. La definición del trigger coincidió entre origen y prueba por SHA-256: `3157c7b1c5604fb970301765674fd5732e3cf2d5ebde6afbdd045fd01c0e714f`. Primero se cambió exclusivamente `sincronizado_en` en la copia. Después se incrementó `visualizaciones_del` en uno, mediante tres commits independientes, siempre en la copia.
5. Antes de cada cambio se calculó una huella MD5 agregada de `to_jsonb(raw_secop)`, ordenada por ID. Después se comparó con la huella de las nuevas `datos_anteriores`, ordenadas por `raw_secop_id`. Coincidieron las tres instantáneas completas; los conteos fueron exactamente 2 000, 4 000 y 6 000.
6. Se midieron `pg_relation_size`, `pg_indexes_size`, `pg_total_relation_size` y `pg_column_size` después de cada commit. Al terminar, la huella de las 2 000 filas del origen seguía siendo `ef5bf0dfc2b97eeb5f599399104015b0` y el OID del origen seguía intacto. Se escribieron **cero filas en el origen**.
7. La base temporal ocupaba 34 856 295 bytes. Se retiró únicamente después de comprobar su OID, la ruta exacta del clúster y cero conexiones. La consulta posterior confirmó su ausencia. Se conservaron la integración, las generaciones únicas y todos sus respaldos.

La ejecución inicial se detuvo antes de crear la base por un error de acceso al cursor. La reanudación comprobó la misma huella de muestra y la ausencia del destino antes de crearlo. No se repitió una carga completa de SECOP. La [evidencia estructurada](HISTORIAL_CAPACIDAD_SECOP_20261006.json) conserva etapas, huellas y resultado final; no contiene filas crudas ni credenciales.

## Capacidad ilustrativa para decidir retención

Aplicar el promedio de esta muestra a una versión de los registros modificados produce estos escenarios:

| Fracción del corte que cambia una vez | Historial adicional aproximado |
| --- | ---: |
| 1 % | 187,16 MiB |
| 10 % | 1,83 GiB |
| 100 % de 9 249 545 registros | 18,28 GiB |

Son extrapolaciones, no crecimiento productivo observado. Excluyen WAL, respaldos, otros objetos de la base y cambios futuros en contenido, compresión o profundidad de índices. Tres modificaciones deliberadas no permiten inferir una frecuencia diaria de actualización. El disparador no archiva una fila recién insertada ni una modificación que afecte solo la fecha de sincronización; la proyección corresponde a versiones que efectivamente se archivan.

La [decisión de retención](RETENCION_Y_CAPACIDAD_SECOP_20261002.md) debe definir plazo, generaciones preservadas, ubicación de archivo y autorización de eliminación. Esta medición aporta el costo observado y deja explícitas sus limitaciones; no reconstruye la identidad de filas anteriores al trigger ni aprueba la eliminación de evidencia histórica.
