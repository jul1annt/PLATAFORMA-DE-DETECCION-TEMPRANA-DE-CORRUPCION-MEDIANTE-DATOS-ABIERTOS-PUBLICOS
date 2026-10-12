# Activación local verificada — 12/10/2026

**Backend y worker `794d185` activos en este equipo; frontend `9362d94`.** El usuario aceptó el perfil y autorizó la activación: «Acepto el perfil y activa localmente». La base publicada es `plataformaanticorrupcion:5432`, OID 24577, rol ordinario `plataforma_operacion`, esquema **`3c19a8f7e2d0`**. [Informe estructurado](ACTIVACION_LOCAL_VERIFICADA_20261012.json).

Interfaz: <http://127.0.0.1:4173>. API: <http://127.0.0.1:8000/docs>. El aviso conserva **corte histórico SECOP del 01/10/2026** y las fuentes permanecen pausadas.

## Cambio ejecutado

1. Se verificaron paquete, runtime, destino y referencias HTTP; se detuvieron los tres componentes de forma ordenada y se comprobó ausencia de clientes externos en la base.
2. Se creó un nuevo checkpoint administrativo/esquema con snapshot consistente después de detener los servicios. Configuración y exportaciones quedaron protegidas en `Backend/.codex-integration-postgres/activation-execution-20261012/frozen-checkpoint/`. Es privado porque contiene secretos. Se conserva el respaldo histórico único y su prueba de recuperación anterior.
3. Pasaron las migraciones ensayadas: `08c6d9a2e4b1` en **3,544 s**, `2ab7c4e8d910` en **4,044 s** y `3c19a8f7e2d0` en **391,024 s**. El índice de fecha/ID se construyó una vez y terminó válido/listo; se aprovechó el reemplazo compacto existente. El resumen se inicializó sin actualizar contratos.
4. Se verificaron **9.249.545 crudos y 9.249.545 procesados**. Los seis contadores del resumen coincidieron con un agregado independiente del universo completo. Hay 21 índices válidos/listos de contratos, cero índices inválidos en crudos/procesados y los cuatro triggers de calidad habilitados. Las huellas UTC acotadas y el estado administrativo coincidieron antes/después de las migraciones. Se preservó el original legado, OID 17930.
5. Se instalaron los bindings preparados y arrancaron API, interfaz y worker con la misma revisión de backend. Calidad, tablero y distribución conservaron las referencias HTTP previas. La fecha del corte siguió visible.

No hubo recarga ni normalización del corte. Las escrituras administrativas de las pruebas —una sesión y un trabajo de exportación— son distintas de los contratos. Los checkpoints, generaciones y paquetes anteriores se conservaron; los cambios Git permanecen locales.

## Flujo real y worker

Pasaron **19 comprobaciones HTTP**: acceso sin sesión rechazado, login, identidad administrativa, fuentes pausadas, página de sincronizaciones, búsqueda/detalle, calidad, vacío, validación de límites, exportación, logout y sesión revocada. El worker completó `EXITOSO` una exportación CSV de **un contrato**, 275 bytes, con checksum verificado y descarga por capability.

El primer helper de smoke se detuvo antes de cualquier llamada HTTP: al copiar su fuente UTF-8 con la decodificación predeterminada de Windows se alteró la etiqueta del archivo de credenciales. Se corrigió exclusivamente la lectura del helper, se conservó el informe fallido y se ejecutó el flujo. Las credenciales y el código de la aplicación no cambiaron por ese incidente.

## Perfil aceptado en el destino publicado

Ocho lectores continuos, cuatro rutas, dos minutos y sin pausa entre solicitudes: **9.083/9.083 respuestas correctas**, cero errores HTTP/contenido y cero errores del observador. Límites aceptados: búsqueda p95 ≤1 s y calidad p95 ≤3 s.

| Ruta | Solicitudes | p95 | Máximo |
| --- | ---: | ---: | ---: |
| Búsqueda 2024 | 2.270 | 0,283 s | 0,538 s |
| Búsqueda vacía | 2.269 | 0,0065 s | 0,492 s |
| Calidad | 2.271 | 0,0048 s | 0,0945 s |
| Proveedores | 2.273 | 0,308 s | 0,466 s |

Se identificaron **diez conexiones de la API** mediante puertos TCP y PID nativos, ligados a sesiones PostgreSQL. Sus inventarios fueron iguales antes/después. Esto no demuestra que no existiera una conexión transitoria entre esas capturas. Las huellas acotadas, resumen y último trabajo también coincidieron antes/después del perfil. Los servicios permanecen funcionando; fuentes y trabajos activos: cero.

Las 25 muestras cubrieron el generador, el árbol completo del supervisor desplegado —API, frontend y worker— y todo el clúster PostgreSQL :5432. Máximo privado en una misma captura: **373.616.640 bytes**; mínimo físico disponible: **5.335.818.240 bytes**; mínimo disco libre: **82.959.581.184 bytes**; intervalo máximo: **5,040 s**. Se verificó cobertura nativa de los backends visibles por SQL. Se excluyen :5433 y otras aplicaciones del equipo; son muestras, no picos continuos.

## Alcance de cierre y reversa

**P16 cerrado para el perfil local aceptado.** El recorrido completo, la interrupción HTTPS/TLS, la pérdida controlada de un backend/lease y la exclusión/recuperación de workers conservan la evidencia de `ec9b5d2`; los árboles Git de módulos y migraciones son idénticos en `794d185`. Startup/pool y el perfil HTTP publicado se comprobaron por separado. Se conservan los dos timeouts de los ensayos largos anteriores. Este perfil no es otro ensayo conjunto de nueve millones de escrituras con fallos y no fija rendimiento para cualquier demanda o generación futura. [Pruebas previas y límites](../auditoria/VALIDACION_LOCAL_PENDIENTES_20261011.md).

La reversa preparada conserva el esquema expandido y declara su revisión real al volver a la aplicación anterior. Su lectura HTTP sobre ese esquema se verificó en la copia completa existente; no se ejecutó una reversa en la base publicada. La búsqueda anterior carece del desempate por ID del candidato. [Preparación y secuencia de reversa](ACTIVACION_LOCAL_PREPARADA_20261012.md).

Los manifiestos de preparación y los informes anteriores con candidato inactivo/95 puntos permanecen como snapshots históricos. Este despliegue verificado los sucede. La nueva configuración activa prepara diez conexiones, overflow cero, timeout de conexión de 60 s y búsquedas/proveedores sin workers paralelos.

## Estado del plan

**96/101 completados (95,0 %); cinco pendientes (5,0 %):** P01 egreso/firewall con autorización explícita pendiente, P05 identidad anterior y retención del historial, P06 contraste con DIAN autorizado, P12 linaje legado con evidencia de extracción anterior y P15 aprobación/aplicación de conservación de respaldos. [Checklist vigente](../auditoria/PLAN_DE_ACCION.md). Esta activación no aplicó reglas de firewall ni eliminó respaldos.
