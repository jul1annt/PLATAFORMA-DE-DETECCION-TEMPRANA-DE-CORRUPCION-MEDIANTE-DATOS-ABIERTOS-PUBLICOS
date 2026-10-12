# Validación local de los seis pendientes

Estado: **en ejecución; 95/101 puntos completos y seis abiertos**. Fecha: 11/10/2026, Bogotá. El usuario pidió terminar los pendientes en este equipo. Los commits y artefactos preparados se mantienen locales.

## Estado por punto

| Punto | Trabajo disponible | Requisito pendiente |
| --- | --- | --- |
| P01, egreso | Seis reglas preparadas para los dos ejecutables del runtime dedicado; otros programas y perfiles globales no cambian. | La revisión automática rechazó ejecutar su aplicación sin autorización explícita para esas reglas. La pregunta con el alcance exacto está pendiente; ninguna aplicación o bloqueo de destinos se acredita. |
| P05, historia previa | Reconciliación agregada y crecimiento medido de 6.000 versiones reutilizados. | Evidencia de identidad anterior y decisión de conservación. No se asignan IDs oficiales por similitud de contenido. |
| P06, proveedores | Código de normalización y validación del NIT disponible. | Archivo o acceso DIAN autorizado para contrastar la identidad histórica; no se dispone de una ruta entregada por el usuario. El dígito de verificación no sustituye ese contraste. |
| P12, linaje legado | Original preservado y detalle individual de 18.980 filas cotejadas contra 105.640 candidatas del corte del 01/10: 3.470 sin coincidencia exacta y 157 tuplas ambiguas. El diagnóstico anterior del 30/09 conserva sus 3.405 casos. | Evidencia anterior de extracción/identidad para explicar los casos individuales. Las clasificaciones alternativas y los cortes distintos no se suman. |
| P15, retención | [Propuesta concreta e inventario local](../operacion/RETENCION_LOCAL_PROPUESTA.md). | Aprobación de la política y constancia de aplicación. Se mantienen generaciones únicas, originales y respaldos verificados; no se habilitan vencimientos por silencio. |
| P16, carga y recuperación | Corte completo y recuperaciones verificados en `ec9b5d2`. Mitigación local `794d185` con 395 pruebas y piloto preparado: 9.884/9.884 correctas, cero conexiones nuevas bajo los ocho lectores. | Aceptación del perfil/límites, evaluación de los incidentes y despliegue con verificaciones posteriores. Las pruebas separadas no equivalen a repetir un ensayo conjunto largo del nuevo startup. |

## Artefacto local y comprobaciones terminadas

El candidato `ec9b5d2297cbb0ed4f7a0cff58038333e8ee110d` contiene el resumen transaccional de calidad, las opciones de paralelismo por ruta y la corrección de paginación. Se empaquetaron **198 archivos y compilaron 185 fuentes Python**, con SHA-256 por archivo y cotejo de las fuentes probadas. Las diferencias de CRLF/LF se distinguen de cambios de código.

- **366 pruebas backend nativas pasaron en 38,22 s** sobre una base sintética pequeña e independiente. El índice de paginación pasó upgrade/downgrade/upgrade. Se reutilizó esa base pequeña después de las 351 pruebas del primer arreglo; los fixtures nunca apuntaron a la copia de nueve millones.
- La paginación usa el ID como desempate en ambos sentidos. Ocho regresiones de búsqueda descendente fallaban antes del arreglo; los veinte casos de búsqueda pasaron después. La corrección está en `85329b7`; el índice correspondiente está en `ec9b5d2`.
- OpenAPI, matriz de accesos y dependencias del paquete pasaron. Las comprobaciones de importación usan claves sintéticas y prohíben conexiones SQL. El paquete parcial se cotejó con su ZIP conservado antes de continuar tras una falta de configuración sintética.
- Los nueve gates locales previos pasaron: pip check, OpenAPI, matriz de accesos, auditoría Python, tipos API, pruebas frontend, lint, auditoría npm y build con URL externa. Los locks y árboles frontend/tipos son idénticos en el nuevo candidato, por lo que se reutilizan esas evidencias y se repiten las comprobaciones del código backend cambiado. No se afirma una instalación limpia nueva ni CI remoto.

## Copia completa y lectura

Se creó una sola copia nativa de `plataforma_integracion_local:5433`, conservando el origen: **9.249.545 crudos/procesados**, 129.062 anomalías y cuatro analíticas. La copia de ensayo es `codex_plan_full_acceptance_20261011_test:5433`, **OID 75045**. La copia tardó 706,43 s; las migraciones del resumen no recargaron ni normalizaron los contratos. El resumen se cotejó contra un agregado independiente del universo completo.

El piloto de ocho clientes continuos durante 120 s sobre el candidato anterior `6a5cb46`, con cero workers paralelos solo en búsqueda/proveedores, obtuvo **10.047/10.047 respuestas correctas**. Búsqueda de 2024: p95 **0,279 s**; calidad: **0,005 s**. Las 25 capturas incluyeron el generador, API e hijos Python, más todo el clúster PostgreSQL :5433. Máximo privado en una misma captura: 237.510.656 bytes; mínimo físico disponible: 5.204.975.616 bytes. Son mediciones muestreadas del piloto, no límites aceptados ni prueba conjunta terminada.

Al combinar escrituras, la validación encontró que los empates de fecha podían mover filas de página. Añadir el ID expuso un coste de lectura de 4.228 filas empatadas: **14.334 ms** en una consulta. La migración concurrente `3c19a8f7e2d0` añade `ix_cp_fecha_publicacion_id`; su construcción en la misma copia tardó **121,08 s** y ocupa **291.766.272 bytes**. La consulta posterior tardó **48,859 ms**. Es una comparación puntual de planes; el perfil conjunto debe medir sus latencias bajo carga. Se conservaron el heap, las huellas acotadas antes/después del DDL y la configuración publicada.

## Recuperación y ensayo conjunto

El caso TLS independiente sobre la copia completa pasó: 10.001 sintéticos, **5.000 filas confirmadas antes del corte y 5.001 retomadas**, seis intentos fallidos, cursor y ventana conservados, cero duplicados y exclusión de workers vivos. Se verificaron certificado y hostname con una autoridad efímera local; el destino del transporte se redirigió a loopback. La limpieza se limitó a los IDs recién creados de ese caso. El informe original fallido se mantiene separado del diagnóstico posterior exitoso; no se atribuye una causa no demostrada al primer error de integridad.

El ensayo conjunto conserva cada intento:

1. La primera captura dejó fuera una conexión SQL que apareció después del inventario. Se canceló exclusivamente su consulta de preparación, con PID, inicio de sesión, consulta y OID comprobados; la transacción se revirtió y no se encoló trabajo.
2. El observador corregido pasó 24 capturas y 9.858 respuestas correctas. La preparación masiva de 10.000 cambios agotó el límite de dos minutos y se revirtió.
3. El primer lote de 1.000 cambios confirmó su commit. La búsqueda detectó el problema de desempate; los siguientes cambios se revirtieron. El arreglo y el índice se validaron por separado.
4. Una expectativa incorrecta del validador sobre el tamaño de página se detuvo antes de escribir. El informe y artefactos se conservaron.
5. La continuación verificó y reutilizó el lote confirmado y completó los restantes cambios de prueba. Un argumento incorrecto del harness impidió ejecutar TLS; además, su señal de parada lanzada después del commit dejó los contadores del log en cero aunque las primeras 1.000 proyecciones ya estaban confirmadas. Se conservó ese estado y se corrigió el harness para detenerse antes del siguiente commit. No se fabricó un checkpoint.
6. El worker comprobó que esas 1.000 filas ya estaban actualizadas y las omitió. Con ocho lectores y un worker de reprocesamiento vivos, **pasaron la interrupción HTTPS con certificado verificado, la exclusión de workers vivos, la pérdida controlada de un único backend PostgreSQL y la recuperación por otro proceso**. El ensayo acumuló 81.861 solicitudes y una búsqueda vacía agotó su timeout de 30 s. Se detuvo y conservó el checkpoint confirmado en **828.000 filas**, con 9.066 procesadas y 818.934 omitidas. El p95 de búsqueda fue 0,296 s y el de calidad 0,005 s; ese timeout impide tratarlo como un perfil sin errores.
7. Se reanudó exclusivamente el tramo restante desde 828.000, sin copiar, restaurar ni preparar los datos otra vez. El reintento explícito conservó los tres intentos previos y el límite de recuperación automática. Las solicitudes llevan un ID de diagnóstico; se registran fases HTTP, tiempos SQL, PID del backend y eventos de espera, sin cuerpos, texto SQL, parámetros ni credenciales. Un error de transporte se conservó y no reinició el procesamiento; una respuesta con contenido incorrecto habría detenido el ensayo. **Terminó con datos verificados y un timeout preservado.** El tramo anterior y esta continuación se informan por separado; no equivalen a un único ensayo ininterrumpido sin fallos.

### Resultado terminal de la continuación

El trabajo 106 cerró `EXITOSO`, inactivo, con cuatro intentos conservados. El total acumulado fue **9.249.545 evaluados: 9.667 procesados y 9.239.878 omitidos**. La continuación confirmó **8.421.545 filas nuevas evaluadas en 8.422 lotes**, además del prefijo confirmado de 828.000. Su duración de worker fue 4.081 s; ese tiempo corresponde al tramo retomado, no a una transformación inicial de nueve millones de escrituras. La mediana no se exporta en este informe; el p95 por lote fue 0,672 s y el máximo 7,379 s.

- **308.043 respuestas correctas de 308.044 solicitudes** en la continuación; un timeout en proveedores. El tramo anterior conserva sus 81.861 solicitudes y su propio timeout en búsqueda vacía.
- Búsqueda de 2024: p95 **0,325 s**; calidad: **0,0054 s**; proveedores: **0,310 s**; búsqueda vacía: **0,0074 s**. Los umbrales propuestos de p95 se cumplieron; no se registra aceptación del responsable ni se ocultan los errores de transporte.
- **835 capturas** de recursos, cero errores del observador, máximo privado en una misma captura de 386.949.120 bytes, mínimo físico de 4.272.939.008 bytes y mínimo libre en disco de 82.837.897.216 bytes. El intervalo máximo real fue **8,431 s**, aunque la espera nominal fue de cinco segundos. Son muestras, no una medición continua de picos.
- Crudos y origen conservado pasaron el cotejo de conteos, máximo ID y huella UTC de las primeras 2.000 filas. El resumen coincide con un agregado independiente del universo completo. Se comprobaron 21 índices válidos, cero inválidos, cero trabajos activos y hashes de configuración publicados iguales.
- El cotejo adicional de estadísticas de campos faltantes verificó todos sus campos presentes, conteos y porcentajes; ninguna anomalía quedó sin referencia al contrato procesado. Fue una transacción de solo lectura.
- API, lectores, worker y observador del ensayo terminaron. La aplicación publicada sigue activa con su versión anterior.

Los recursos se capturan cada cinco segundos con PID y fecha de creación. La conexión de observación se adquiere antes del inventario; los backends nuevos que aparecen después se cotejan con reintentos acotados registrados. El ensayo incluye todo el clúster :5433; excluye los procesos :5432, aunque ambos comparten recursos del equipo. Las reservas exigidas son 2 GiB físicos y 25 GiB libres en disco. Cada parada conserva el checkpoint; ningún timeout habilita borrar o restaurar otra vez el corte.

La continuación registró un timeout en proveedores. La solicitud llegó a la API a las **18:55:29 UTC** y su backend PostgreSQL se creó en ese instante; el proceso permaneció con 0,03125 s de CPU y sin sesión SQL visible durante las capturas siguientes. La primera ejecución SQL empezó **55,53 s después**; las dos consultas registradas tardaron 0,00035 s y 0,831 s. La respuesta terminó a los 56,36 s, después del límite del cliente de 30 s. La evidencia localiza la espera en el arranque/establecimiento de esa conexión; no demuestra todavía su causa interna ni permite atribuir la misma causa al timeout anterior. La memoria física disponible durante esas capturas superó 4 GiB. El worker continuó, conservando el incidente para el resultado final.

Durante ese periodo también hubo una búsqueda auxiliar por nombres de archivos en Descargas, Documentos y Escritorio, detenida a las 18:56:04 UTC. Ese proceso de la herramienta no forma parte del árbol privado medido del generador/API; las reservas físicas sí reflejan el uso compartido del equipo. No se demuestra una relación causal con el timeout. El ensayo no se presenta como una ejecución con el equipo dedicado exclusivamente a la carga.

Después del cierre se midieron tres conexiones nuevas de solo lectura: **146,72 ms, 47,48 ms y 46,98 ms** para quedar disponibles, con consultas de metadatos de 3–5 ms. No se modificaron SSL/GSS ni parámetros de seguridad. La demora anterior no se reprodujo en esas tres conexiones sin carga HTTP; esto no demuestra su causa ni acredita una corrección del arranque bajo carga.

El detalle individual de linaje terminó mediante búsquedas indexadas y resultados transmitidos por lotes: **18.980 originales frente a 105.640 candidatas**, comparando 60 campos fuente del corte aceptado del 01/10. La lectura tardó 599,37 s y estuvo limitada por E/S. El original conserva `c7e3a91b5d24`, donde la columna Socrata aún no existe; se leyó sin migrarlo y se conservaron las huellas UTC acotadas de ambas bases.

| Clasificación alternativa del corte del 01/10 | Única | Ambigua | Sin coincidencia |
| --- | ---: | ---: | ---: |
| Contenido exacto en 60 campos | 15.392 | 118 | 3.470 |
| Tupla diagnóstica de adjudicación | 18.115 | 157 | 708 |

Cada fila original tiene un caso privado con cardinalidades, IDs de candidatas y campos diferentes de las candidatas más próximas. Las listas se limitan a veinte candidatas; los conteos incluyen todas. El archivo `legacy-cases.jsonl` contiene 10.145.604 bytes y SHA-256 `4cb38055eecad6453659c4e1d9cc193202236dcd139538f025107fbfa7c8f0d3`. Se escribieron **cero filas en las bases y se asignaron cero identidades oficiales**. El cotejo agregado del 30/09 se conserva como una comparación distinta; ni sus categorías ni sus resultados se suman a los del 01/10. [Contexto y límites de linaje](LINAJE_LEGADO.md).

## Mitigación posterior de preparación del pool

Se añadió el candidato local **`794d185832c7c56ffa4d91ef08ca1f3d15128be5`**. Sus cambios son configuración de pool/espera de conexión, preparación del startup y su supervisión; los árboles Git de repositorios, worker, ingesta y migraciones son idénticos a `ec9b5d2`. El recorrido completo anterior se conserva como evidencia de esos componentes. La configuración nueva y su startup se verificaron por separado; no se afirma que el ensayo conjunto largo se repitió con esta preparación.

La primera suite de 395 pruebas pasó, pero el chequeo nativo posterior rechazó `127.0.0.1/32`. Se conservó el informe y la base vacía, se corrigió a `host(inet_server_addr())` y **395 pruebas pasaron otra vez en 36,34 s**. La preparación real de diez slots independientes tardó **0,264 s**; las transacciones se cerraron y sus ajustes quedaron restaurados. No se recreó esa base ni se aplicaron fixtures al corte completo.

El paquete nuevo contiene **200 archivos y 187 fuentes Python compiladas**, con hashes y equivalencia de las fuentes probadas, locks idénticos, OpenAPI y matriz de accesos comprobados con conexiones SQL prohibidas durante importación. El paquete anterior se conserva y las configuraciones activas no cambiaron.

En el corte completo existente, un piloto de lectura de **120,10 s y ocho clientes continuos** obtuvo **9.884/9.884 respuestas correctas**, sin errores ni conexiones creadas después del startup. Búsqueda p95 **0,269 s**, calidad **0,0048 s**, proveedores **0,265 s**. Las 25 capturas no tuvieron errores; máximo privado en una misma captura: 235.188.224 bytes, mínimo físico: 4.965.335.040 bytes, intervalo máximo: 5,156 s. Huellas acotadas, cola y resumen coincidieron antes/después; el servidor del piloto terminó. Esta prueba no hizo escrituras, normalización ni carga del corte.

Los umbrales propuestos se cumplen en estos pilotos; la solicitud de aceptación del responsable se presenta con estos resultados concretos. [Configuración, alcance y activación](../operacion/PREPARACION_POOL_LOCAL.md).

La base sintética de la preparación, OID 26620, se retiró después de cerrar pruebas y piloto: cero contratos, cero trabajos activos, cero sesiones y tamaño de 26.615.143 bytes. El retiro anterior de la base de pruebas de paginación fue de 26.918.247 bytes. La copia completa sigue usada para la validación/activación pendiente; originales, paquetes y respaldos se conservan.

## Base publicada

**Actualización posterior del 12/10:** el usuario aceptó el perfil y autorizó la activación. Backend/worker `794d185` y esquema `3c19a8f7e2d0` están activos; conteos y agregado independiente pasaron, el smoke real completó 19 comprobaciones/exportación y el perfil publicado obtuvo 9.083/9.083 correctas. **P16 cerrado para el alcance local; checklist 96/101, cinco pendientes.** [Despliegue y límites](../operacion/ACTIVACION_LOCAL_VERIFICADA_20261012.md). Los párrafos y el JSON anteriores son registros de la fase previa, sin modificar sus timeouts o límites.

La [preparación de activación del 12/10](../operacion/ACTIVACION_LOCAL_PREPARADA_20261012.md) respaldó el esquema y las cuatro tablas administrativas con un snapshot consistente. La restauración aislada pasó después de incorporar colación/enum desde el esquema; se conservaron los intentos detenidos y se retiró solo la base temporal propia. Se prepararon seis archivos privados de activación/reversa sin reemplazar bindings. No se repitió copia, dump, restauración o procesamiento del corte histórico; aceptación y despliegue siguen pendientes.

La base publicada continúa con el histórico **01/10/2026**, backend/worker `915e863`, interfaz `9362d94` y esquema `f4826b9d1c30`. Las configuraciones activas se cotejaron mediante hashes; el resumen y el índice nuevo solo están aplicados en la copia de ensayo. El original de 18.980 filas, generaciones únicas y respaldos siguen preservados.

El postflight de las **02:18 UTC del 12/10 (21:18 del 11/10 en Bogotá)** confirmó PostgreSQL 15.19, OID 24577, rol ordinario, componentes vivos, respuestas 200 de API/interfaz, cero fuentes/trabajos activos, 21 índices válidos, huellas UTC acotadas de crudos/procesados y hashes de configuración iguales. El candidato no se activó y el resumen todavía no existe en la base publicada.

Evidencias privadas reproducibles: `Backend/.codex-integration-postgres/full-acceptance-20261011`, manifiesto del candidato `releases/ec9b5d2297cb/candidate.json` y `indexed-pagination-local-tests-20261011.json`. Los informes públicos no incluyen credenciales, JWT, claves ni archivos de entorno.
