# Escrituras evitadas en reprocesamiento sin cambios

Estado: corrección y regresión PostgreSQL verificadas; ensayo del universo completo en curso.

## Costo encontrado

El servicio contaba un contrato como `omitido` cuando su huella normalizada, confianza y banderas de calidad seguían iguales, pero actualizaba siempre `procesado_en`. En un recorrido forzado, esa escritura de metadatos puede repetir millones de actualizaciones sin cambiar la proyección. No sustituye la evaluación de reglas ni la reconciliación de anomalías.

La nueva prueba observa las sentencias SQL reales. Contra el método de `7a72c883` falla: aparece un `UPDATE contratos_procesados SET procesado_en` aunque el contrato no cambió. Con la corrección, ese caso no emite ningún UPDATE del contrato y conserva su fecha anterior.

## Cambio

Se actualiza `procesado_en` cuando cambia la proyección de datos/calidad o cuando se consume una sincronización cruda más reciente. Si la proyección y el watermark ya están al día, el recorrido forzado evalúa las reglas y reconcilia anomalías, pero evita la escritura del contrato. El log de procesamiento sigue registrando que esa fila fue evaluada.

La distinción importa para el siguiente incremental: una fuente puede traer una fila cuyo contenido normalizado es igual. Esa sincronización nueva sí se consume y la prueba confirma que el siguiente recorrido tiene cero candidatos. La corrección no deja filas en un ciclo de pendientes ni omite cambios en calidad.

## Evidencia

`OPTIMIZACION_REPROCESAMIENTO_SIN_CAMBIOS_20261005.json` registra:

- La regresión del método anterior, con un UPDATE innecesario observado.
- Cero UPDATE del contrato en el caso forzado sin cambios ni nueva sincronización.
- Un UPDATE para consumir la nueva sincronización de contenido normalizado igual.
- Cero candidatos en el incremental posterior.
- **248 pruebas backend aprobadas**, sin fallos ni omisiones, en PostgreSQL 15 migrado a `d2804c8b39a1`.
- Eliminación de la base de regresión vacía, de 25 550 183 bytes, tras comprobar cero sesiones. La lectura de la base operativa confirmó 18 980 crudos/procesados.

## Ensayo a escala

La copia temporal contiene los **9 249 545** registros del corte histórico conservado; no hubo otra descarga de SECOP. El primer observador no detectó el estado ORM expirado y no activó su pausa. Se terminó únicamente el backend de ese ejecutor tras confirmar **26 000** filas (5 000 con cambios y 21 000 omitidas), se detuvo su controlador temporal y se conservó el avance durable.

Se corrigió el observador, se añadieron otros 5 000 cambios controlados en filas aún no visitadas y un segundo proceso retomó **el mismo trabajo 100** desde 26 000. El corte fuente y la base operativa no recibieron esas modificaciones. El recorrido completo, las búsquedas HTTP concurrentes y el muestreo de procesos siguen activos; `RECUPERACION_ESCRITURAS_ESCALA_20261005.json` es su estado en curso, no un cierre.

El ensayo declara la reparación del observador, la falta de latencias de lote/HTTP de las primeras 26 000 filas y la pausa del muestreo mientras no había ejecutor. Las latencias del tramo optimizado no constituyen una comparación controlada del tiempo total entre versiones. No se da por cerrado P16 hasta verificar el resultado completo y revisar sus criterios de aceptación.
