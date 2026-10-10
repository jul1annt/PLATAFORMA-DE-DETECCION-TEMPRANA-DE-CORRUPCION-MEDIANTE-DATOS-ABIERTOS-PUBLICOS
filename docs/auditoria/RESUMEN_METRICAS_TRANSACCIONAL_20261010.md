# Resumen transaccional de calidad — 2026-10-10

Estado: **candidato local implementado y verificado; no desplegado en el corte publicado**. El plan conserva **95/101 (94,1 %), seis pendientes**.

## Cambio

La migración `2ab7c4e8d910`, posterior al índice compacto `08c6d9a2e4b1`, crea una fila de `public.contratos_metricas_calidad`: total, incompletos, sospechosos, alto riesgo, cantidad con confianza y suma de confianza. El promedio conserva el denominador que excluye valores nulos; cero sigue siendo un valor válido. No almacena contratos, nombres, IDs de origen ni copias de sus contenidos.

La inicialización cuenta una vez la tabla existente después de obtener `SHARE ROW EXCLUSIVE`; requiere aislamiento `read committed` para tomar una instantánea posterior a los escritores previos. El bloqueo y el conteo tienen límites locales de 5 s y 120 s. Los objetos y el backfill se confirman juntos; un fallo revierte esta migración. No se cambia configuración global ni se normalizan contratos.

Altas y bajas usan triggers por sentencia con relaciones de transición; UPDATE utiliza un trigger por fila, con `WHEN` que solo lo ejecuta si cambia una contribución a las métricas. Calcula diferencias directas, sin sumar relaciones de transición por cada UPDATE del ORM. Cambios solo de fecha, nombres o clasificaciones que siguen fuera de ALTO no escriben el resumen. TRUNCATE lo pone a cero en la misma transacción. [PostgreSQL 15 documenta relaciones de transición y condiciones de triggers](https://www.postgresql.org/docs/15/sql-createtrigger.html).

Los incrementos son expresiones sobre la fila actual, protegidas por el bloqueo de escritura de PostgreSQL; contrato y resumen se confirman o revierten juntos. La fila única serializa escritores que cambian métricas y debe medirse bajo la carga conjunta exigida. Las lecturas ven valores confirmados mediante MVCC. Las funciones usan permisos del llamador, tablas destino con esquema explícito y un `search_path` acotado.

## Separación de responsabilidades y compatibilidad

El modelo representa los contadores; la migración/triggers mantienen la invariancia en PostgreSQL. El repositorio obtiene calidad, tablero y distribución de anomalías desde esa fila y conserva el armado de las respuestas. Los DTO, controladores y contrato público no cambian; no hay nuevas dependencias externas.

La presencia de la tabla se consulta una vez por sesión. En una base anterior sin ella y en SQLite se conserva el agregado directo. Con la tabla presente, faltar la fila es un error de integridad: no se oculta repitiendo un conteo completo ni reconstruyendo automáticamente datos. La consulta ORM conserva autoflush. La caché de presencia solo vive en la sesión; ejecutar migraciones con servicios cerrados y nuevas sesiones al abrir el artefacto.

## Validación nativa

La versión final pasó **333 pruebas backend en 44,18 s**, con PostgreSQL 15 y rol ordinario. Las 17 nuevas cubren triggers habilitados/tipo, orden y aislamiento de inicialización, altas/bajas/UPDATE, operaciones sin filas, upsert/DO NOTHING, cambios compensados, nulos/cero/fracciones/extremos enteros, equivalencia de las tres respuestas, autoflush, rollback de lotes, TRUNCATE con rollback, fila de resumen ausente, escritores concurrentes y lectura con una sola instantánea.

Upgrade/reversa/upgrade pasaron, también sobre datos existentes del ensayo. Se conservan las corridas previas: 321 aprobadas/12 fallidas por una fuente sintética sin `frecuencia_dias`; luego 333 aprobadas tras corregir esa fixture; otras 333 al revisar UPDATE. La última validación identifica los SHA-256 de los seis archivos actuales. No se atribuye una corrida anterior al código final.

OpenAPI y matriz de acceso coincidieron. No hubo CI remoto del candidato ni despliegue nuevo: la autorización GitHub previamente solicitada sigue pendiente, sin otro intento de publicación.

## Mediciones y coste pendiente

Se reutilizó la misma base sintética identificada, con **10 001 contratos**, para comparar agregación directa y resumen. Cada estrategia recibió 200 lecturas desde ocho clientes: **800/800 resultados correctos** entre la versión inicial y la revisada. Son consultas SQL/repositorio, **no HTTP ni un ensayo de nueve millones**.

| Versión revisada, 10 001 sintéticos | Mediana lectura, ms | p95 lectura, ms | Tres lotes ORM de 1 000 cambios de confianza, s |
| --- | ---: | ---: | --- |
| Agregado directo | 4,228 | 8,863 | 0,295 / 0,297 / 0,316 |
| Resumen | 5,416 | 8,749 | 0,452 / 0,422 / 0,428 |

En este volumen pequeño no se demuestra una mejora relevante de lectura; el plan del resumen devuelve una fila sin recorrer contratos. **Falta medir la mejora real en el corte completo.** Los cambios de métricas añaden aproximadamente **0,11–0,16 s por 1 000 filas** en las muestras revisadas, cerca del 44 % respecto a la mediana del agregado directo. No se oculta este coste ni se acepta automáticamente por quedar debajo de un segundo en esas muestras.

La primera propuesta, UPDATE por sentencia con agregación de relaciones de transición, había dado 0,433–0,449 s frente a 0,262–0,300 s sin resumen. Se conserva el resultado; las condiciones y muestras difieren y no se atribuye toda variación a la revisión. La versión actual evita esa agregación por UPDATE pequeño y añade la condición antes de invocar la función.

Cuatro lotes de cambio solo de fecha conservaron **el mismo `ctid`, total y suma del resumen**: no lo escribieron. Con el trigger activo, la primera muestra tomó **1,176 s** y la posterior **0,315 s**; las referencias con ese trigger temporalmente desactivado en la base sintética tomaron 0,424/0,297 s. No se presenta la muestra caliente como el máximo ni se declara superado un límite de lotes. Los cuatro triggers quedaron habilitados después del ensayo.

## Estado final

Se retiró únicamente `codex_plan_quality_summary_20261010_test`, OID 25627, tras comprobar nombre, clúster, datos sintéticos identificados, pruebas y cero sesiones. Su tamaño antes de retiro fue **28 147 047 bytes**; los reportes/logs permanecen. No se eliminó ninguna generación o respaldo único.

La base publicada conserva **`f4826b9d1c30`, 21 índices válidos/cero inválidos y ninguna tabla de resumen nueva**, archivo de heap 24736, huellas UTC acotadas iguales y máximo de trabajos 103. Fuentes y cola siguen inactivas. API, frontend y worker permanecen en los artefactos aplicados `915e863`/`9362d94`.

Siguiente paso dependiente: autorización de publicación, CI y despliegue compatible, inicialización única sobre el corte, cotejo independiente y perfil HTTP completo con escrituras/fallos. La [guía operativa](../operacion/RESUMEN_METRICAS_TRANSACCIONAL.md) fija esas comprobaciones. Calidad, coste de escritura, contención, aceptación del perfil y escenarios conjuntos mantienen **P16 abierto**; no se cierra el plan por un ensayo menor.

[Evidencia estructurada](RESUMEN_METRICAS_TRANSACCIONAL_20261010.json): corridas, trazas de lectura, lotes ORM, planes, hashes del código/logs y postflight. Se comprobó ausencia de secretos activos y JWT antes de guardarla localmente.
