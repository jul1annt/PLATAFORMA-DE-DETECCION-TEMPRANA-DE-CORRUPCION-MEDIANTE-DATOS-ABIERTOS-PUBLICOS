# Agregados de métricas, despliegue y recuperación de CI — 2026-10-09

Estado: cambio implementado, validado y desplegado en este equipo. El plan conserva **93/101 puntos completos y ocho pendientes**. Esta entrega mejora una consulta y restablece la ejecución de CI; no acredita la aceptación completa de P16 ni la promoción de otro corte.

## Cambio y comprobación de resultados

Calidad, tablero y distribución de anomalías usan ahora `COUNT(*) FILTER (WHERE ...)` para contar condiciones. El total usa `COUNT(*)` sobre una tabla cuya clave primaria no admite valores nulos. Se conservan el promedio, redondeo, categorías, porcentajes, tratamiento de nulos y una sola sentencia por consulta. No se agregó caché ni se modificó el contrato HTTP.

Cuatro pruebas locales pasaron: datos vacíos, categoría de confianza, agregación del universo completo y nulos en indicadores/confianza. El caso nuevo verifica que un valor de confianza cero participa en el promedio y que indicadores nulos no cuentan como verdaderos. El ORM modificado se ejecutó con transacciones de solo lectura y rol ordinario sobre el corte de nueve millones; sus resultados completos coincidieron con las respuestas de las tres rutas de la versión anterior.

## Comparación SQL sobre el corte conservado

Se verificaron los mismos resultados en **48 consultas**, con cuatro conexiones ocupadas continuamente y dos lecturas por conexión en cada ronda. La referencia fue 9 249 545 contratos, 127 626 incompletos, 1 424 sospechosos y cero de alto riesgo, con el mismo promedio exacto. Se alternaron rondas del SQL anterior y del filtrado. Los tiempos incluyen la ejecución SQL y su recepción; son muestras pequeñas posteriores a una lectura de referencia.

| Consulta | Trabajadores paralelos por Gather | Muestras | Mediana, s | p95, s |
| --- | ---: | ---: | ---: | ---: |
| `CASE`, anterior | 2 | 16 | 1,601 | 2,753 |
| `FILTER`, nueva | 2 | 16 | 1,473 | 2,176 |
| `CASE`, diagnóstico serial | 0 | 8 | 1,744 | 1,745 |
| `FILTER`, diagnóstico serial | 0 | 8 | 1,531 | 1,549 |

Con la configuración paralela existente, la reducción de mediana observada fue aproximadamente **8 %**. El diagnóstico serial mostró una reducción de aproximadamente 12 %. Los ajustes de paralelismo se hicieron con `SET LOCAL` únicamente en las transacciones de prueba y se verificó su reversión; **el despliegue conserva el valor existente de 2**. No se modificaron ajustes globales ni índices. Los percentiles usan rango más próximo y no establecen un SLA.

## CI: fallo externo y corrección comprobada

Los dos CI del commit de lógica `ac7cdcc` fallaron en `Initialize containers`: Docker Hub rechazó los tres intentos automáticos de descargar `postgres:15` por límite de solicitudes sin autenticar. No ejecutaron las pruebas backend. La interfaz pasó. La evidencia conserva el error original y no lo presenta como un fallo de pruebas de aplicación.

Se cambió el servicio de CI a `public.ecr.aws/docker/library/postgres:15`. La [galería del editor Docker](https://gallery.ecr.aws/docker/) identifica esas imágenes mantenidas por Docker; [AWS documenta su descarga pública](https://docs.aws.amazon.com/AmazonECR/latest/public/public-gallery.html). La comprobación directa del registro verificó **PostgreSQL 15.19** y el mismo digest Linux/amd64 en ECR y Docker Hub: `sha256:a5f9ead8ed7cb25abc36bea51fb9bb2be8d5579ed4ef3d28876027e438391ff0`. No se cambió la versión mayor ni el rol restringido de pruebas.

El commit desplegado **`83382f9a5d2a95da2ff5201429cc59074488f8fe`** pasó ambos CI:

- PR [37993062270](https://github.com/jul1annt/PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS/actions/runs/37993062270).
- Push [37993056254](https://github.com/jul1annt/PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS/actions/runs/37993056254).
- **264 pruebas backend**, sin omisiones; seis frontend; contratos publicados, lint/build y auditorías correctos, sin vulnerabilidades conocidas en los locks comprobados.

El uso de la etiqueta mayor `15` conserva la política anterior de actualizaciones menores del servicio CI. La igualdad de digest describe la imagen verificada el 09/10; no garantiza que ambas etiquetas cambien simultáneamente en el futuro.

## Despliegue real y tráfico concurrente

Se verificaron hashes de dependencias/ejecutable/bundle, identidad de base y ausencia de trabajos activos. Se detuvo el conjunto anterior y se comprobó su cierre antes de cambiar el manifiesto. Backend y worker arrancaron desde el archivo Git inmutable de `83382f9`; la interfaz reutiliza el bundle de `9362d94`, tras comprobar que el árbol frontend completo es idéntico. El manifiesto previo quedó conservado para reversa y existía un resguardo de restaurar ese manifiesto si fallaban arranque o comprobaciones.

Las tres respuestas HTTP completas de calidad, tablero y distribución de anomalías coincidieron por SHA-256 antes y después. La base sigue siendo `plataforma_integracion_local:5433`, OID 74053, revisión `f4826b9d1c30`, rol ordinario y 20 índices; no se aplicó una migración, descarga ni transformación. Las fuentes continúan pausadas y el corte histórico sigue identificado como 01/10/2026. La versión anterior y los respaldos se conservaron.

Sobre la nueva versión se ejecutó el mismo perfil piloto de ocho clientes continuos y cuatro rutas, con lanzamientos durante 120 s y cierre en **120,818 s**. Las **875/875 respuestas HTTP 200** coincidieron con sus referencias. Se conservaron las huellas acotadas de crudos/procesados y el máximo de trabajos, sin escrituras de contratos ni trabajos nuevos.

| Consulta | Correctas / total | Mediana, s | p95, s | Máximo, s |
| --- | ---: | ---: | ---: | ---: |
| Búsqueda de 2024 | 217/217 | 0,339 | 1,021 | 1,922 |
| Vacío de 2099 | 219/219 | 0,004 | 0,011 | 0,361 |
| Calidad global | 221/221 | 2,901 | 7,449 | 11,834 |
| Diez proveedores | 218/218 | 0,426 | 1,260 | 10,065 |

La búsqueda p95 todavía supera el segundo de la propuesta. Calidad p95 fue superior a las muestras del 06/10: **esta ejecución no demuestra una mejora de las latencias HTTP más lentas**. La mejora SQL aislada y los perfiles HTTP de días diferentes tienen alcances distintos; no se atribuye toda la variación al cambio de expresión ni se ajustan límites para declarar cumplimiento.

Se tomaron 27 muestras de recursos, con separación máxima 5,090 s. Incluyeron al menos diez procesos del árbol de aplicación, con PID/fecha de creación comprobados; el máximo privado muestreado de aplicación fue **212 107 264 bytes (202,28 MiB)**. Memoria física disponible mínima: aproximadamente **5,70 GiB**; disco libre mínimo: **107,75 GiB**. PostgreSQL sigue limitado a los backends visibles de la base, sin todos los procesos del clúster; el muestreo no acredita máximos continuos. La [propuesta de carga](CRITERIOS_ACEPTACION_CARGA_PROPUESTA.md) mantiene perfil, umbrales y escenarios conjuntos pendientes.

La [evidencia estructurada](OPTIMIZACION_METRICAS_20261009.json) conserva consultas SQL, muestras, resultados ORM, fallo inicial de CI, comprobación del registro, despliegue y solicitudes del ensayo. No contiene contraseñas, tokens de los registros ni cuerpos de contratos. El PR permanece en borrador; el plan completo no se declara terminado.
