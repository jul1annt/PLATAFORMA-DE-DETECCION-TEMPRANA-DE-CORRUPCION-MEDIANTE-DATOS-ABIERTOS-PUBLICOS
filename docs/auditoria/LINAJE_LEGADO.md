# Linaje de las filas SECOP heredadas

Estado: diagnóstico reproducible; la identidad individual de las filas indicadas abajo sigue sin demostrarse.

La comparación de solo lectura entre `plataforma_cutover_restore_check` y `plataforma_cutover_test` del 2026-09-30 está en [RECONCILIACION_SUBCONJUNTO_LEGACY.json](RECONCILIACION_SUBCONJUNTO_LEGACY.json). Se ejecutó con `Backend/scripts/reconcile_legacy_raw_subset.py`. Las 18 980 filas heredadas no tienen `socrata_row_id`; sus 18 980 identificadores de proceso sí aparecen en el corte SECOP comparado, pero esos procesos producen 105 640 filas candidatas. En 478 procesos hay varias filas candidatas.

| Resultado de comparación | Filas heredadas | Alcance |
| --- | ---: | --- |
| Coincidencia exacta y única en 60 campos fuente | 15 456 | Equivalencia de contenido en ese corte; no prueba identidad Socrata anterior. |
| Coincidencia exacta con varias candidatas | 119 | El contenido no distingue una adjudicación concreta. |
| Sin coincidencia exacta | 3 405 | Los atributos difieren o falta la fila; se requiere evidencia adicional para atribuir la causa. |
| Tupla de adjudicación única | 18 120 | Coincidencia diagnóstica, no clave oficial. |
| Tupla de adjudicación ambigua | 157 | Hay más de una candidata con la misma tupla. |
| Sin coincidencia de tupla | 703 | La tupla no permite asociar la fila. |
| Tupla coincidente con otros atributos distintos | 2 702 | No demuestra si cambió SECOP, el procesamiento anterior o ambos. |

La tupla diagnóstica usa fuente, proceso, adjudicación, código y NIT de proveedor, y valor adjudicado. Las categorías de coincidencia exacta y de tupla son clasificaciones alternativas del mismo universo y **no se suman entre sí**. Los recuentos por campo incluyen empates de candidatas y tampoco son recuentos de contratos distintos. Las diferencias más frecuentes en candidatos cercanos son `codigo_pci` (1 290), `ciudad_de_la_unidad_de` (934) y `codigo_principal_de_categoria` (441).

No se copiarán IDs Socrata de una generación posterior a las filas heredadas basándose solo en proceso o tupla. Para resolver una fila hace falta un registro anterior con ID Socrata, una bitácora verificable de extracción con identidad de fila, o una clave de negocio demostrada como única para esa adjudicación y versión. Hasta disponer de esa evidencia, el respaldo original y el informe agregado preservan el estado anterior; la conciliación histórica total permanece abierta en P12 del plan.

## Detalle individual local del 11/10/2026

Se cotejó directamente el original conservado `plataformaanticorrupcion_pre_20261010:5432`, OID 17930, contra el corte aceptado del **01/10/2026** en `plataforma_integracion_local:5433`, OID 74053. El original mantiene `c7e3a91b5d24`; su columna Socrata todavía no existe. Se usaron transacciones de solo lectura, sin migrar ni escribir filas en esas bases.

El universo de 18.980 originales produjo 105.640 candidatas. En 60 campos fuente, hubo **15.392 coincidencias exactas únicas, 118 ambiguas y 3.470 sin coincidencia**. La tupla diagnóstica tuvo **18.115 únicas, 157 ambiguas y 708 sin coincidencia**. Estos resultados corresponden a otro corte y no sustituyen los recuentos del 30/09 expuestos arriba. Las dos clasificaciones son alternativas y no se suman.

El archivo privado `Backend/.codex-integration-postgres/full-acceptance-20261011/legacy-cases.jsonl` ofrece un caso por fila, cardinalidades y campos diferentes de las candidatas más próximas. Sus listas se limitan a veinte candidatas; los conteos abarcan todas. Tiene 10.145.604 bytes y SHA-256 `4cb38055eecad6453659c4e1d9cc193202236dcd139538f025107fbfa7c8f0d3`. El [informe público de validación](VALIDACION_LOCAL_PENDIENTES_20261011.json) contiene la procedencia y los totales, sin los valores de los registros.

Todas las identidades anteriores continúan marcadas como no demostradas. Se asignaron **cero IDs oficiales** a las filas originales y las huellas UTC acotadas antes/después coincidieron. El detalle permite investigar casos concretos; no recupera una identidad anterior ausente ni acredita conciliación histórica total.
