# Ingesta ante un corte real de conexión HTTPS

Fecha: 2026-10-05 UTC. Resultado: **prueba PostgreSQL y suite completa aprobadas**.

## Qué se comprobó

La prueba `Backend/tests/test_ingesta_network_postgres.py` ejecuta el worker, servicio, paginación y reintentos del adaptador SECOP con **10 001 filas sintéticas**. Un servidor HTTPS local presenta un certificado temporal validado y usa el nombre/SNI esperado. Solo se sustituye el destino de transporte dentro del test; las reglas de endpoints y DNS de producción permanecen intactas.

Después de persistir un primer lote de 5 000 filas, el servidor anuncia una respuesta JSON completa, envía solo un fragmento y cierra realmente el socket TLS. El cliente detecta el cuerpo incompleto; **no se sustituye la excepción ni se simula `urlopen`**.

| Comprobación | Resultado |
| --- | --- |
| Filas confirmadas antes del corte | 5 000 |
| Intentos HTTPS fallidos de esa página | 6, límite real del adaptador |
| Trabajo interrumpido por la fuente | ERROR, inactivo; cursor conservado |
| Watermark tras el error | Sin avanzar |
| API durante la espera del corte | HTTP 200, EN_PROCESO |
| Reclamación por otro worker / recuperación de abandonados | No reclamado / 0 |
| Encolado duplicado mientras estaba activo | Devuelve el mismo trabajo |
| Cursor de la siguiente ejecución | `wire-04999` |
| Filas traídas e insertadas al retomar | 5 001 |
| Universo final / IDs distintos | 10 001 / 10 001 |
| Historial de filas duplicado por relectura | 0 |
| Solicitudes HTTPS totales | 9 |

La consulta con la que retoma la siguiente ejecución es igual a la que falló, incluida la ventana original; termina desde `wire-09999` con la última fila. Solo entonces avanza el watermark y limpia el checkpoint. El fallo de red es terminal para ese trabajo; no se lo reencola indefinidamente. La nueva ejecución es un trabajo distinto solicitado por el test.

## Evidencia y limpieza

La prueba individual pasó; la suite completa pasó con **249 pruebas, cero fallos y cero omitidas**, en 32,62 s según la salida de pytest. `RECUPERACION_RED_INGESTA_20261005.json` registra la observación emitida por la prueba, SHA-256 del archivo, revisión Alembic, alcance y comprobaciones de limpieza.

La base aislada `codex_plan_resume_test` se retiró después de confirmar cero filas de ensayo y cero sesiones activas; ocupaba **20 061 543 bytes**. Después se confirmó ausencia de otros clientes y se detuvo limpiamente el clúster aislado. La base operativa de 5432 conserva **18 980 filas crudas y procesadas**, comprobadas en solo lectura. No se creó otra copia del universo histórico completo ni se descargaron datos públicos.

## Límites de cierre

La interrupción ocurre en sockets HTTPS reales con una fuente sintética local. La consulta de estado usa TestClient; no es una medición de la red desplegada. Esta prueba no combina un fallo del proveedor público con búsquedas concurrentes sobre nueve millones de contratos. El ensayo de ese universo y su fallo PostgreSQL se documenta por separado en `RECUPERACION_ESCRITURAS_ESCALA_20261005.md`.

P16 sigue pendiente de criterios de aceptación y de la cobertura que se exija para el entorno de despliegue. Este ensayo amplía la evidencia de red y continuidad del cursor sin declarar cerrado un alcance mayor.
