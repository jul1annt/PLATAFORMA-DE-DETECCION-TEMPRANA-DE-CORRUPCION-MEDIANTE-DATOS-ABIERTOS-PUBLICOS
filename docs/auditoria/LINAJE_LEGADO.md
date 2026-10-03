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
