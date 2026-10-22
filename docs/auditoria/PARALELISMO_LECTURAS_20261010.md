# Paralelismo de lecturas — 2026-10-10

Estado: **opciones locales preparadas y verificadas; desactivadas, sin nuevo despliegue ni publicación externa**. El plan conserva **95/101 (94,1 %), seis pendientes**.

## Diagnóstico y alcance

Se reutilizó el corte publicado de 9 249 545 contratos en `plataformaanticorrupcion:5432`, OID 24577, esquema `f4826b9d1c30`, con rol ordinario, fuentes pausadas y cola inactiva. Las transacciones fueron de solo lectura. No hubo extracción, normalización, copia del universo, construcción de índices ni ajuste global de PostgreSQL.

La consulta real del repositorio para 2024 conservó **1 670 370 coincidencias y 20 filas**. El primer acceso completo tomó 1,049 s; los EXPLAIN posteriores tomaron **101,094 ms para contar** y **0,043 ms para la página**. El conteo usó el índice existente de fecha, dos workers y cero Heap Fetches; la página usó su recorrido inverso. La búsqueda vacía de 2099 conservó cero resultados. Estos tiempos individuales con cachés distintas no prueban el p95 HTTP ni justifican añadir otro índice.

## Comparaciones SQL concurrentes

Ocho clientes en circuito cerrado alternaron las cuatro lecturas existentes: búsqueda, vacío, calidad y proveedores. Cada variante recibió dos pasadas de 20 s, con orden contrabalanceado y cierre de solicitudes pendientes. Los límites se aplicaron con `set_config(..., true)` únicamente a cada transacción de lectura. **No son perfiles HTTP de aceptación**: excluyen controlador, serialización de respuesta y red; tampoco combinan escrituras o fallos.

La comparación uniforme dio **966/966 resultados correctos** y 27 capturas de recursos; la comparación selectiva dio **664/664 correctos** y conserva sus capturas. Los resultados se verificaron por hash de la salida del repositorio: conteo e IDs ordenados para las búsquedas, objeto de métricas y lista de proveedores para las otras lecturas. Las huellas acotadas de filas, máximo de trabajos, inicio del postmaster y configuración global coincidieron antes/después. No se afirma un hash completo del universo ni un máximo continuo de memoria.

| Límite de workers por consulta | Búsqueda p95, s, dos pasadas | Calidad p95, s, dos pasadas | Proveedores p95, s, dos pasadas |
| --- | --- | --- | --- |
| Dos en todas las lecturas | 1,077 / 0,873 | 4,102 / 4,036 | 1,437 / 0,972 |
| Uno en todas las lecturas | 0,938 / 0,901 | 4,085 / 3,889 | 1,449 / 1,099 |
| Cero en todas las lecturas | 0,359 / 1,024 | 3,773 / 8,868 | 0,342 / 0,603 |
| Dos en todas, referencia de la comparación selectiva | 1,222 / 1,078 | 4,582 / 4,567 | 1,445 / 1,484 |
| Dos en calidad, cero en búsqueda/vacío/proveedores | 0,358 / 0,553 | 4,863 / 5,170 | 0,322 / 0,317 |

El ajuste selectivo mejoró las dos rutas pequeñas en este experimento y empeoró el p95 de calidad. Desactivar todo el paralelismo fue inestable. El circuito cerrado aumenta la presión cuando otra ruta termina antes; no se atribuye cada variación exclusivamente a un parámetro. **Se conserva el valor global de dos y no se activa ninguna opción en la integración publicada.**

También se comparó un agregado agrupado por las cuatro claves del índice con el agregado filtrado vigente. En seis lecturas contrabalanceadas coincidieron conteos y promedio redondeado a dos decimales. El primer acceso directo tomó 1,446 s, pero las dos lecturas directas posteriores tomaron **0,518 y 0,506 s** frente a **0,632–0,647 s** agrupadas. Sus EXPLAIN tomaron 0,617 y 0,712 s. No se sustituyó el SQL vigente por una alternativa más lenta en estas lecturas calientes.

## Implementación y separación de responsabilidades

`core/read_database.py` incorpora dependencias de sesión específicas para `/api/procesados/search` y `/api/procesados/metricas/top-proveedores`. Reciben la sesión de `get_db`, que conserva la responsabilidad de cerrarla en todos los desenlaces. La política usa parámetros enlazados y un ajuste local a la transacción; no se cambia el SQL ni el filtrado del repositorio.

`SEARCH_QUERY_PARALLEL_WORKERS` y `PROVIDER_QUERY_PARALLEL_WORKERS` son opcionales, enteros entre 0 y 1024. **Omitirlas conserva el comportamiento anterior**; cero es un valor explícito. Las demás rutas, exportaciones y worker mantienen su dependencia habitual. No se añade dependencia externa. La [guía operativa](../operacion/PARALELISMO_LECTURAS.md) exige verificar el perfil HTTP completo antes de activar valores en un artefacto desplegado.

## Validación y estado final

- **316 pruebas backend pasaron en 35,53 s**, con PostgreSQL y rol ordinario, sobre una base sintética nueva. Las 18 nuevas cubren límites, ausencia de opción, SQLite, alcance de rutas, independencia de ajustes y reutilización del mismo backend del pool después de rollback, commit y transacción fallida por un error SQL real.
- Upgrade/reversa/upgrade del esquema pasaron. El primer intento no ejecutó pruebas porque el Python del runtime no incluye pytest; se conservó y se retomó la misma base con el entorno de desarrollo existente, sin instalar paquetes ni repetir migraciones.
- La base sintética se retiró tras comprobar su OID, clúster y cero sesiones. Los logs y reportes permanecen. OpenAPI y matriz de acceso coincidieron; `git diff --check` no encontró errores de whitespace.
- Postflight canónico: **21 índices válidos, cero inválidos**, esquema `f4826b9d1c30`, cero trabajos activos/fuentes habilitadas, máximo de trabajos 103 y huellas UTC acotadas iguales. API, interfaz y worker siguen activos en `915e863`/`9362d94`. Las opciones siguen ausentes de `runtime.env`.

La publicación GitHub continúa pendiente de la autorización solicitada después del rechazo automático anterior; no hubo otro intento ni mecanismo alternativo. Las nuevas opciones no están desplegadas ni medidas en HTTP. P16 mantiene aceptación del perfil, optimización de calidad y cobertura conjunta; no se cierran casillas por estos pilotos SQL.

[Evidencia estructurada](PARALELISMO_LECTURAS_20261010.json) conserva planes, trazas para recalcular percentiles, capturas resumidas con identidades, SHA-256 de reportes privados completos, hashes del código probado, validación y postflight. Se comprobó ausencia de secretos activos y JWT antes de guardarla localmente.
