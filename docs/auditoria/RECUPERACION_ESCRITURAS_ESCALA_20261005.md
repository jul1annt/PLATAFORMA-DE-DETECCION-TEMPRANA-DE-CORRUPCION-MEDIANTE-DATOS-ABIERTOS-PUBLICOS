# Recuperación del reprocesamiento con escrituras a escala

Fecha: 2026-10-05 UTC. Resultado: **verificado y copia temporal eliminada**.

## Alcance y resultado

Se utilizó una copia aislada del corte histórico conservado de SECOP: **9 249 545 filas crudas y contratos procesados**, en PostgreSQL 15, puerto 5433. Se conservaron los 18 índices y los commits durables. No hubo otra descarga, recálculo de analíticas ni promoción del corte.

Se modificó el valor de 5 000 filas iniciales y se terminó el backend PostgreSQL del primer worker después de un avance confirmado de **26 000 filas**. Tras reparar el observador se modificaron otras 5 000 filas aún no visitadas. Un segundo proceso recuperó el **mismo trabajo 100**, intento 2, desde el ID 26 000. La traza contiene un ancla y 9 224 lotes contiguos: **9 223 545 filas adicionales**, sin repetir el prefijo.

El trabajo terminó `EXITOSO`, inactivo, con **9 249 545 evaluadas, 10 162 procesadas y 9 239 383 omitidas**. Las 10 000 modificaciones controladas quedaron reflejadas en los contratos. El contador de procesadas incluye otras diferencias de proyección/calidad y no se presenta como el número exclusivo de modificaciones del ensayo.

El primer log quedó `ERROR` con 26 000 confirmadas; el segundo, `EXITOSO`, conserva el universo y fecha de referencia del trabajo. Las **128 900 anomalías activas** concuerdan con el resultado; las estadísticas de campos faltantes coinciden con sus agrupaciones. Los 18 índices permanecieron válidos y disponibles.

## Mediciones

| Medida | Resultado observado |
| --- | ---: |
| Recorrido recuperado, ancla a último lote | 1 894,64 s, aproximadamente 31,6 min |
| Ritmo de ese recorrido | 4 868 filas/s |
| Latencia de lote: mediana / p95 / máximo | 0,169 / 0,245 / 50,047 s |
| Consultas concurrentes | 504/504 HTTP 200 |
| Estado del trabajo: mediana / p95 / máximo | 164,6 / 274,3 / 655,0 ms |
| Búsqueda de 2024: mediana / p95 / máximo | 313,3 / 593,4 / 931,5 ms |
| Muestras de recursos | 845, intervalo nominal de 5 s |
| Máxima suma de memoria privada de procesos propios | 284,8 MiB |
| Máxima suma de working sets de procesos propios | 2 081,9 MiB |

La API local recibió rondas de ocho solicitudes: cuatro de estado y cuatro búsquedas de 2024. Todas las búsquedas conservaron **1 670 370 coincidencias y 20 resultados por página**. Los percentiles usan rango más próximo. Las trazas distinguen cada petición y lote, incluidos los lentos, y cada proceso observado.

El ritmo excluye la copia inicial (794,06 s), el piloto, la pausa de reparación y la reconciliación final. Incluye los lotes recuperados con cambios. Los reprocesamientos antiguos con millones de inserciones no constituyen una comparación equivalente; este resultado no demuestra un factor de aceleración para una carga totalmente nueva.

## Instrumentación y límites

El observador inicial no registró el estado ORM expirado, por lo que no activó la pausa prevista tras el primer lote. La interrupción real ocurrió después de 26 000 filas. Ese prefijo carece de trazas de latencia de lote y HTTP; sus muestras completas de recursos se conservaron. Durante la reparación no había un ejecutor activo. La optimización que evita actualizar fechas de contratos ya consumidos entró en el proceso recuperado; el informe registra su SHA-256 y separa esta etapa del piloto.

El cierre automático del informe se detuvo al comparar objetos UUID devueltos por PostgreSQL con sus cadenas JSON. Una consulta independiente confirmó que los valores serializados, conteos, cuatro analíticas y huella de las primeras 5 000 filas eran exactamente iguales al origen. Se completó únicamente el cotejo y la limpieza, **sin volver a ejecutar el worker**. Las líneas completas de la traza comprimida interrumpida se salvaron en un archivo cerrado; el original también se conserva localmente.

Los recursos incluyen el controlador/API, workers propios y descendientes del postmaster aislado; excluyen el clúster operativo de 5432. Son máximos muestreados: procesos breves o picos entre muestras pueden faltar. La suma de working sets puede contar memoria compartida varias veces. El máximo de working set de vida informado por Windows para cada PID puede incluir actividad anterior al ensayo. Estas cifras no equivalen a memoria física exclusiva ni a un SLA de producción.

Falta acordar criterios de aceptación y completar la cobertura del ensayo que se exija para despliegue, incluido fallo de red de la fuente. **P16 sigue abierto; el checklist permanece en 90/101.** No se requiere repetir esta copia y recorrido para conservar el resultado ya demostrado.

## Preservación y espacio

El cotejo posterior preservó el origen: **9 249 545 crudos/procesados, 129 062 anomalías y cuatro analíticas**. La comprobación de contenido cubre las primeras 5 000 filas, no una huella completa del origen. La base operativa de 5432 conserva **18 980 crudos y procesados**, comprobados en una transacción de solo lectura.

Se eliminó únicamente `codex_secop_recovery_scale_20261005_test`, sin sesiones activas y después de todos los cotejos. Su tamaño era **22 747 258 215 bytes**; el espacio libre observado aumentó aproximadamente **21,2 GiB**. Después de confirmar ausencia de otros clientes, el clúster aislado se detuvo de forma limpia. Permanecen las generaciones históricas y sus respaldos únicos. La política de retención P15 sigue pendiente.

## Evidencia reproducible

El informe `RECUPERACION_ESCRITURAS_ESCALA_20261005.json` contiene resultados, límites, comprobación independiente, máximos por PID y SHA-256 de los artefactos. La carpeta del mismo nombre conserva las trazas comprimidas de lotes, HTTP y recursos, junto con la interrupción del piloto. No incluye credenciales ni contenidos de contratos.

Desde la raíz del repositorio, `python docs/auditoria/verificar_recuperacion_escala.py` verifica las huellas, continuidad del cursor, contadores y percentiles mediante la biblioteca estándar, sin conectarse a ninguna base. El control pasó con **9 224 lotes, 504 HTTP 200 y 845 muestras**. Las 248 pruebas backend y ambos CI del código `1ee916b` también pasaron; no se volvió a ejecutar la suite para este informe documental.
