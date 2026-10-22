# Índice compacto de métricas — 2026-10-10

Estado: **candidato local válido y medido; migración formal, nuevo backend y CI remoto pendientes**. El plan conserva **95/101 (94,1 %), seis pendientes**.

## Cambio y estado real

Se añadió `ix_cp_metricas_replacement` en la base publicada `plataformaanticorrupcion:5432`, OID 24577, con las cuatro columnas del agregado. El índice contiene **65 798 144 bytes (62,75 MiB)** frente a **460 054 528 bytes (438,74 MiB)** del anterior: 85,7 % menos almacenamiento para esta representación del índice. El anterior permanece; **no se contabiliza ese tamaño como espacio liberado**.

`COUNT(*)` no necesita el `id` incluido en el índice anterior. Eliminar `INCLUDE` permite deduplicar las claves repetidas, según [PostgreSQL 15](https://www.postgresql.org/docs/15/btree-implementation.html#BTREE-DEDUPLICATION). Se conserva cada fila mediante sus TIDs; no se deduplican ni eliminan contratos. La migración `08c6d9a2e4b1` verifica tabla, método, columnas, validez y estado listo del reemplazo antes de retirar el anterior. Reanuda después de crear o retirar el índice, y su reversa restaura `INCLUDE`.

El **estado operativo actual** sigue siendo backend/worker **`915e863`**, interfaz **`9362d94`**, revisión **`f4826b9d1c30`**, rol ordinario y fuentes pausadas, ahora con **21 índices válidos y cero inválidos**. El agregado de calidad ya utiliza el candidato. El código local también cambia el conteo de distribución de riesgo a `COUNT(*)`; no está desplegado y el backend aplicado todavía necesita el índice anterior para su `COUNT(id)`. No retirar ese índice antes de desplegar y comprobar el cambio compatible.

Se respaldó la metadata local antes de actualizar su conteo a 21. La actualización no cambia rol, puerto, OID, revisión, claves ni artefactos. No hubo reinicio de servicios, nueva extracción, normalización o restauración de nueve millones.

## Construcción y recuperación

El primer preparativo HTTP agotó 30 s antes de ejecutar DDL; se reutilizó la referencia de calidad del [piloto canónico verificado](RECURSOS_CARGA_CANONICA_20261010.md) después de cotejar sus huellas y cola. La construcción concurrente posterior alcanzó validación, pero terminó por `lock_timeout=5s` dejando solo el candidato inválido. Se conservó el anterior válido y se comprobó que ya no había transacciones abiertas; no se atribuye el bloqueo a un proceso sin evidencia.

Un único `REINDEX INDEX CONCURRENTLY` recuperó el candidato, con guardas de identidad/forma, fuentes pausadas y cola vacía. Se usó `lock_timeout=120s`, memoria de mantenimiento de 128 MiB y cero workers de mantenimiento **solo en esa sesión**, manteniendo el límite de sentencia de 30 min. La recuperación tardó **369,704 s**. [PostgreSQL documenta esta recuperación de índices inválidos](https://www.postgresql.org/docs/15/sql-reindex.html). No se modificó el catálogo manualmente para marcarlo válido. El postflight confirmó 21 índices válidos/cero inválidos y los valores globales habituales de mantenimiento: 64 MiB y dos workers.

Antes/después coincidieron huellas UTC de 2 000 crudos/procesados, máximo de trabajos **103** y archivo de heap **24736**. La respuesta completa de calidad coincidió por SHA-256. La huella acotada no es un hash exhaustivo; las operaciones realizadas fueron DDL de índices, sin SQL de escritura de contratos.

## SQL y perfil HTTP observado

El nuevo plan empleó `Parallel Index Only Scan` sobre el candidato, dos workers y cero Heap Fetches. Una lectura tomó **1,419 s**, frente a **10,155 s** en la lectura diagnóstica anterior. El plan pasó de 55 740 a 7 976 bloques leídos por PostgreSQL. Son muestras individuales con cachés y condiciones distintas; esos bloques no equivalen necesariamente a lectura física desde disco.

El perfil volvió a usar ocho clientes continuos, cuatro rutas alternadas y 120 s de lanzamientos. Terminó en **121,513 s**, con **1 017/1 017 HTTP 200 y cuerpos correctos**, referencias iguales al piloto anterior y huellas/cola conservadas.

| Consulta | Correctas | Mediana, s | p95, s | Máximo, s |
| --- | ---: | ---: | ---: | ---: |
| Búsqueda 2024 | 253/253 | 0,482 | 1,226 | 1,781 |
| Vacío 2099 | 255/255 | 0,004 | 0,006 | 0,098 |
| Calidad | 257/257 | 2,439 | 3,850 | 4,479 |
| Diez proveedores | 252/252 | 0,563 | 1,255 | 2,948 |

Calidad p95 bajó de **14,988 a 3,850 s** entre estos perfiles; búsqueda subió de 0,675 a 1,226 s. El circuito cerrado produce más solicitudes al acelerar una ruta: 1 017 frente a 372, con observadores distintos. No se atribuye toda variación al índice ni se afirma que todas las rutas mejoraron. **Búsqueda y calidad siguen fuera de los límites de 1 s y 3 s propuestos y no aprobados.** No se ajustan límites para declarar aceptación.

## Instrumentación y pruebas

Dos perfiles iniciales del candidato se detuvieron por guardas del observador: 82 y 565 respuestas correctas, sin acreditar los 120 s completos. Se conservaron separados. El observador final mide recursos una vez por PID/fecha durante la adquisición, comprueba luego identidad con derechos limitados y completa únicamente procesos nuevos/reutilizados hasta lograr un inventario final consistente, con máximo ocho pasadas. Una raíz reemplazada o una lectura faltante falla; no se convierten en una captura completa.

El ensayo final obtuvo **26 muestras válidas**, intervalo máximo **5,343 s**, adquisición máxima con reintentos **0,327 s**, 24 adquisiciones descartadas y dos cambios de inventario reconciliados. Máximo seis intentos por muestra, dos pasadas internas; cero errores finales. Incluyó diez procesos de aplicación, 19–28 del clúster y el generador; no hubo ramas excluidas. Máximo privado conjunto dentro de una captura: **394,43 MiB**; memoria física disponible mínima **5,04 GiB**, disco libre mínimo **97,49 GiB**. No hay un instante atómico común de todos los contadores ni garantía de máximos continuos o de todos los procesos transitorios.

La base pequeña de validación, con rol ordinario, pasó upgrade/reversa/upgrade y **297 pruebas nativas para `6a1d8af`** en 46,90 s. Se retiró solo esa base sintética, 17 915 239 bytes, tras verificar OID y cero sesiones. Después de ajustar observación y `COUNT(*)` de riesgo, pasaron **37 pruebas focalizadas**; OpenAPI y matriz de acceso coincidieron. El cotejo nativo de riesgo comparó `COUNT(id)`/`COUNT(*)` en el universo de **9 249 545**, con igualdad por grupo; ese corte tiene un solo grupo, y las pruebas focalizadas cubren grupos diferentes. No se atribuye la suite anterior al nuevo código completo sin repetir su validación remota.

## Publicación y pendiente

La revisión automática rechazó el push a GitHub por falta de autorización explícita para el repositorio exacto. El commit `6a1d8af` quedó local; se solicitó permiso para la rama existente del PR #1. **No se reintentó ni se publicó por otro mecanismo.** El nuevo artefacto y la retirada formal del índice anterior esperan CI y despliegue compatible conforme a la guía.

[Evidencia estructurada](OPTIMIZACION_INDICE_METRICAS_20261010.json): construcción fallida/recuperación, planes, perfil completo, pilotos incompletos, contadores, pruebas y postflight. Se comprobó ausencia de secretos activos y JWT antes de guardar esta evidencia local. P16 sigue abierto para aceptación del perfil, optimización adicional y combinación de escrituras/fallos/múltiples workers acordada. Las fuentes y el histórico permanecen conservados.
