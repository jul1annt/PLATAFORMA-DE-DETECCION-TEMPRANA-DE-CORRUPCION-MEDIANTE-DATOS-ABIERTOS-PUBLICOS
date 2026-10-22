# Recursos de la carga de lectura publicada — 2026-10-10

Estado: **lecturas verificadas e instrumentación ampliada; P16 abierto**. El plan conserva **95/101 (94,1 %), seis pendientes**.

## Perfil y resultados

API/worker `915e863cc7492e619888506f59a04c6dbbfa5552`, corte histórico en `plataformaanticorrupcion:5432`, OID 24577. Se verificaron rol ordinario, revisión `f4826b9d1c30`, 20 índices válidos, fuentes pausadas y cero trabajos activos. La interfaz conservada es `9362d94`.

Ocho clientes públicos continuos alternaron cuatro rutas, sin pausa entre respuestas. Hubo 120 s de lanzamientos y **124,758 s** hasta cerrar solicitudes. Las referencias se obtuvieron antes; no se simula una caché fría. Preparación y comprobaciones incluidas: 15:12:36–15:14:50 UTC. Las **372/372 respuestas HTTP 200** coincidieron por SHA-256 del JSON completo. La búsqueda de 2024 conservó **1 670 370** coincidencias y 20 elementos; 2099 devolvió cero y lista vacía.

| Consulta | Correctas | Mediana, s | p95, s | Máximo, s |
| --- | ---: | ---: | ---: | ---: |
| Búsqueda 2024 | 92/92 | 0,452 | 0,675 | 1,013 |
| Vacío 2099 | 94/94 | 0,026 | 0,128 | 0,133 |
| Calidad global | 96/96 | 8,906 | 14,988 | 15,040 |
| Diez proveedores | 90/90 | 0,515 | 0,711 | 0,781 |

Percentiles de rango más próximo, desde solicitud hasta recibir cuerpo. **Calidad requiere optimización**; no cumple los 3 s propuestos después para revisión. La búsqueda de esta pasada cumple el segundo propuesto dentro de este perfil; no establece un SLA ni prueba una mejora causada por código.

## Cobertura de procesos y recursos

El [observador Windows](../operacion/OBSERVADOR_RECURSOS_WINDOWS.md) vincula raíz y descendientes por PID/fecha de creación. PostgreSQL se identificó por PID/directorio/puerto de `postmaster.pid`, creación nativa y ascendencia del backend SQL de una conexión verificada. Se excluyó el clúster `:5433`. La creación nativa coincide con el archivo; `pg_postmaster_start_time()` difiere **56,246 s**, permanece estable y se registra por separado sin atribuir causa.

Las **27 muestras aceptadas** incluyeron diez procesos de aplicación, **19–28 del clúster PostgreSQL** y un generador. Todos los backends SQL visibles estaban en el árbol medido. Intervalo máximo: **5,108 s**; adquisición máxima con reintentos: **0,095 s**. Se descartó una adquisición por cambio del inventario; la siguiente fue estable. No hubo errores ni resguardos activados.

| Alcance | Máximo privado muestreado |
| --- | ---: |
| Aplicación, incluidos hijos Python | 227,69 MiB |
| Clúster PostgreSQL presente en las muestras | 126,01 MiB |
| Generador | 43,64 MiB |
| Suma de los tres en una misma muestra | 397,33 MiB |

Memoria física disponible mínima: **4,77 GiB**; disco libre mínimo: **97,34 GiB**. Bytes privados comprometidos no equivalen a memoria física exclusiva. No se acreditan máximos continuos ni todos los procesos transitorios entre muestras. CPU e I/O son contadores acumulados; I/O no equivale a lecturas físicas del disco.

Se preservaron tres intentos previos. El primero guardó solo un checkpoint inicial. El segundo detuvo tráfico por cambios durante captura. El tercero detectó un vínculo cuya fecha de hijo precedía al supuesto padre. Ninguno acredita el ensayo completo. La captura final registra los descartes, permite hasta ocho adquisiciones breves y excluye ramas cuya ascendencia numérica no prueba propiedad; una raíz reemplazada falla inmediatamente. En esta pasada final no hubo ramas excluidas. La comprobación de edades presupone un reloj Windows consistente. **14 pruebas focalizadas del observador pasaron**.

Los preparativos rechazaron una igualdad incorrecta entre tiempos SQL/nativos antes del tráfico. La corrección conserva ambos valores y vincula el backend por su ascendencia real; no altera fechas para obtener igualdad.

## Datos preservados y diagnóstico

Comprobaciones SQL de solo lectura. Las huellas UTC de las primeras 2 000 filas crudas/procesadas coincidieron antes/después; máximo de trabajos **103**. No se escribieron contratos ni se encoló trabajo. No hubo otra extracción, transformación, copia o restauración de nueve millones. La huella acotada no equivale a una comparación exhaustiva.

Una ejecución posterior de `EXPLAIN (ANALYZE, BUFFERS)` del agregado tomó **10,155 s**: `Parallel Index Only Scan`, dos workers, **cero Heap Fetches**, 55 740 bloques leídos por PostgreSQL y 174 hits en el plan. `ix_cp_metricas_cover` ocupaba **460 054 528 bytes (438,74 MiB)**; las 523 586 páginas de la tabla figuraban visibles. No se necesita otro VACUUM completo para obtener visibilidad. Estos bloques pueden proceder de caché del sistema operativo y no prueban por sí solos lectura física desde el HDD.

El agregado ya usa `COUNT(*)`. El `id` incluido impide deduplicación B-tree, según [PostgreSQL 15](https://www.postgresql.org/docs/15/btree-implementation.html#BTREE-DEDUPLICATION). Se preparó `08c6d9a2e4b1`: construye y verifica un reemplazo concurrente con las cuatro columnas del agregado, retira el anterior solo si el nuevo es válido/listo y conserva el nombre final. Reanuda etapas confirmadas y permite reversa a `INCLUDE`. **La aplicación y mejora nativa se comprobarán por separado**; esta evidencia corresponde a `f4826b9d1c30`.

## Evidencia y pendiente

[Prueba estructurada](RECURSOS_CARGA_CANONICA_20261010.json): solicitudes, muestras, huellas, reintentos, intentos previos y plan SQL. Antes de publicar se comprobó ausencia de secretos activos y tokens con forma de JWT.

Se completa la cobertura de árboles PostgreSQL y del generador para este piloto. P16 conserva perfil/límites sin aprobar, optimización de calidad y escenarios conjuntos de lectura, escrituras, red/DB y múltiples workers. La recuperación histórica se reutiliza dentro de su alcance; no se repite una carga completa por defecto.
