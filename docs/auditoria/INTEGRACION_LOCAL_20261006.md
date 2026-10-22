# Integración local, despliegue y recuperación — 2026-10-06 UTC

El usuario eligió este equipo como entorno. API, interfaz compilada y worker dedicado quedan activos en `127.0.0.1:8000` y `127.0.0.1:4173`. La versión desplegada es `9362d94f9dbfbdf352ae11585a2bfd44318b11e6`; los artefactos y Python están separados del entorno de desarrollo. La evidencia estructurada está en [INTEGRACION_LOCAL_20261006.json](INTEGRACION_LOCAL_20261006.json).

## Alcance y resultados

| Comprobación | Resultado |
| --- | --- |
| Integración persistente | `plataforma_integracion_local`, `:5433`, OID 74053; rol ordinario sin superusuario, creación de bases/roles ni replicación. |
| Corte conservado | 9 249 545 crudos y procesados, 129 062 filas de anomalías, cuatro analíticas. Histórico del 01/10/2026, identificado en pantalla; no se afirma frescura oficial actual. |
| Base operativa anterior | `plataformaanticorrupcion:5432` conserva 18 980 crudos y procesados. |
| Fuente histórica | `plataforma_secop_refresh_20261001_test:5433` conserva conteos, huella de las primeras 5 000 filas, revisión `d2804c8b39a1` y 18 índices. |
| Esquema de integración | `f4826b9d1c30`, 20 índices válidos; solo dos índices concurrentes adicionales, sin reprocesar contratos. |
| Fuentes y cola | Fuentes deshabilitadas y sin API keys en la copia, cero trabajos activos al cierre. Los logs de cargas anteriores son historia, no nuevas ingestas. |
| Logs reales | ACL y apertura efectiva de ocho rutas bajo la cuenta de despliegue; solo usuario de despliegue, SYSTEM y Administradores. Sin contraseñas, claves utilizadas ni tokens con forma de JWT en seis archivos de diagnóstico revisados. |
| CI del artefacto | Push [37430770866](https://github.com/jul1annt/PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS/actions/runs/37430770866) y PR [37430776175](https://github.com/jul1annt/PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS/actions/runs/37430776175), ambos correctos: 263 pruebas backend; seis frontend, lint, build y auditorías sin vulnerabilidades conocidas. |

El controlador verifica base, OID, puerto, rol, revisión, hashes de Python/dependencias/bundle y PID con fecha de creación. Registra cada proceso antes de declarar `running`; el cierre exige cola sin trabajo activo. Un fallo de un componente cierra el conjunto sin iniciar un bucle de reinicios. La API y el worker usan la misma versión.

## Demoras corregidas

La consulta global de calidad agotó 120 segundos en el primer ensayo desplegado. Su plan recorría la tabla ancha de contratos. El índice `ix_cp_metricas_cover` permitió usar `Index Only Scan` sin forzar el planificador: el mismo SQL y los mismos conteos tardaron **0,9996 / 0,8258 / 0,8440 s**. El índice ocupa 460 054 528 bytes y se construyó en 269,27 s con el rol ordinario.

El tablero reveló otra lectura costosa: proveedores seguía pendiente después de 176 segundos y el refresco del cliente iniciaba solicitudes superpuestas cada minuto. Limitar primero grupos por NIT conservando el nombre máximo todavía superó 45 s antes de agregar `ix_cp_nit_nombre`. Con ese índice parcial, el SQL final tardó **0,5821 / 0,1267 / 0,1094 s**; el plan usa lecturas del índice para contar y obtener el nombre de los grupos elegidos. Ocupa 5 349 376 bytes y se construyó en 364,54 s. No se truncan nombres ni se agrupan proveedores homónimos. Conteos y `MAX(nombre)` se obtienen en una sola sentencia; los empates se ordenan por NIT. React evita superponer el refresco y distingue la hora de consulta de la fecha del corte.

Las mediciones SQL y las consultas HTTP exitosas están separadas en el JSON. No constituyen un SLA de carga aceptado. Los índices agregan espacio y mantenimiento en futuras escrituras. Véanse [lecturas solo de índice](https://www.postgresql.org/docs/15/indexes-index-only-scans.html) y [construcción concurrente](https://www.postgresql.org/docs/15/sql-createindex.html).

## Cliente real y API desplegada

- Búsqueda de 2024: 1 670 370 coincidencias, 20 filas por página y detalle HTTP correcto.
- Cancelación: una pausa breve y acotada de la tabla de esta integración dejó pendiente la página siguiente. Volver atrás cerró su conexión de búsqueda; al liberar la pausa quedó visible la página 1 correcta. La traza registra solo fecha, método y ruta. La supresión de una respuesta tardía tiene además una prueba frontend independiente. No se afirma que abortar el navegador siempre cancele el SQL en PostgreSQL.
- Filtro de alto riesgo sin coincidencias: Total 0, explicación del vacío y las tres descargas deshabilitadas.
- Servicios detenidos: error de red visible; al iniciar y recargar reaparecieron los resultados.
- Sesión: login real, fuente SECOP inactiva, recarga con sesión, logout y regreso protegido al formulario. El bearer anterior recibió 401 después del cierre.
- Tablero final: volumen, indicadores y proveedores visibles con el aviso del corte histórico.
- API: rechazo anónimo de administración, consulta de fuentes/logs autorizada, vacío para 2099 y límite inválido 422.
- Worker: nueva exportación de un proceso y día concretos, sin barrer todo el universo; entrega HTTP 200 de 262 bytes con SHA-256 `bf43e24ec805c43e98dfbbdbc9039f6f96a06a4cc1a01b0ff3f49e5d01160905`.

El rango de fechas se verificó mediante URL visible y API. El proveedor de navegador no emitió de forma fiable los eventos React al rellenar fechas; no se declara ensayada la escritura manual de esas fechas. La reversa final acumuló 14 comprobaciones HTTP; la recuperación de la versión actual, 21 incluyendo espera y descarga del trabajo.

## Reversa y recuperación por capas

Se cerraron ordenadamente los tres servicios y se verificó su ausencia antes de cada cambio. Se volvió realmente a backend/worker `0c065c4e034c2f4661fcf3a57892195bbaec6fcc` con su bundle anterior y manifiesto de hashes, manteniendo las credenciales, cola y esquema compatible. Después se restauraron backend/worker y bundle `9362d94`. Ambas versiones usan Mako 1.4.2 auditado. No se ejecutó downgrade, recarga de SECOP ni normalización de nueve millones de filas.

La recuperación combina dos evidencias de alcance explícito:

1. **Base histórica completa:** dump de 3 434 770 306 bytes y SHA-256 `c0e885928126013d87c234320392d18e5d4d441c9e1d520b97557e447d8be02f`, restaurado y cotejado independientemente el 03/10. El hash se verificó otra vez antes de preparar esta integración. Se reutiliza [esa evidencia](RESPALDO_RESTAURACION_SECOP_20261003.json); no se hizo otra restauración completa hoy.
2. **Estado local posterior:** con servicios detenidos, se respaldaron `admins`, `admin_sessions`, `fuentes_datos` y `background_jobs`, configuración privada y los tres CSV. El checkpoint final contiene una cuenta, diez sesiones, una fuente y 101 trabajos. El dump de control se restauró en otra base vacía migrada a la cabeza actual; conteos y huellas de cada tabla coincidieron. Se alinearon las secuencias y se comprobó que los IDs siguientes superaban los restaurados. Login/logout funcionaron usando las credenciales y configuración respaldadas.

Además se confirmó y recuperó un fallo reversible del administrador local: con los servicios pausados se desactivó únicamente `admin_local`, se reprodujo el estado desactivado y se repusieron las cuatro tablas de control por sus claves desde las filas de la restauración independiente. Las huellas finales coinciden con el checkpoint; no se truncó `fuentes_datos`, no se usó `CASCADE` y no se reescribió ninguna tabla de contratos. Un resguardo recuperaba ese único cambio de cuenta si el ensayo fallaba. Se eliminó exclusivamente la base pequeña de restauración, con OID, directorio del clúster y ausencia de conexiones comprobados; su tamaño era 9 387 367 bytes. La integración persistente y sus respaldos siguen disponibles.

Esto acredita el checkpoint y la recuperación local ensayados. Un desastre posterior exige reconciliar las escrituras posteriores a ese checkpoint; una restauración del dump histórico por sí sola no incluye las sesiones y exportaciones nuevas. La guía operativa exige mantener escrituras pausadas, restituir el estado por claves, alinear las secuencias y validar las huellas antes de abrir el servicio.

## Cierre del plan y límites pendientes

Se cierran **P02, P10 y P18** para el entorno elegido: **93/101 casillas (92,1 %)**. El PR permanece en borrador y no se promovió el universo a la base operativa anterior.

P01 conserva un bloqueo concreto: Windows rechazó la elevación para aplicar las seis reglas preparadas; el destino no aprobado era accesible en la comprobación previa. Preparar reglas y validar URLs no demuestra egreso bloqueado. Se requiere aplicarlas con permisos de administrador y hacer la comprobación posterior. La lista de IP es una instantánea con vencimiento de 30 minutos, no seguimiento permanente del DNS.

Continúan P05/P12 (linaje previo y ambiguo), P06 (DIAN autorizado), P14/P19 (aceptación del corte, respaldo y promoción), P15 (política de generaciones únicas) y P16 (criterios y cobertura de aceptación de carga). La elección de este equipo resolvió la falta de entorno para los tres puntos cerrados; no responde esas decisiones pendientes.

Se identificó además el artefacto derivado `Backend/.codex-integration-postgres/releases/6c63b309a278`, de 190 010 452 bytes, sin referencias en los manifiestos activos o de respaldo y con fuente conservada en Git. La revisión automática de aprobación rechazó su eliminación con el motivo literal «blocked by policy». La orden no se ejecutó; ese directorio sigue conservado y no se contabiliza como espacio liberado. La integración actual, los artefactos de reversa y los datos no se modificaron por ese intento.

![Integración local con corte histórico visible](INTEGRACION_LOCAL_20261006.jpg)
