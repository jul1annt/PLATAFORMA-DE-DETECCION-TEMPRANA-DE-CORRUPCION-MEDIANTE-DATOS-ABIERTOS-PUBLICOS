# Recuperación local y corrección del inventario — 15/10/2026

## Servicios recuperados

La comprobación encontró PostgreSQL en `127.0.0.1:5432`, pero API, interfaz y worker detenidos. El archivo `services.json` conservaba `phase: running` del 12/10; las identidades de proceso registradas ya no estaban activas. Una consulta independiente de procesos confirmó que no quedaban Python de esa integración. El bloqueo de supervisor era un archivo vacío del 12/10.

Se conservaron los registros anteriores y el bloqueo, se validaron artefactos, identidad de PostgreSQL, rol ordinario y revisión, y se comprobó que los puertos de aplicación estaban libres. Sin fuentes ni trabajos activos, se retiró únicamente el bloqueo obsoleto y se arrancó la versión existente `794d185832c7c56ffa4d91ef08ca1f3d15128be5`.

El supervisor y los tres componentes quedaron activos. API `/openapi.json` e interfaz `/index.html` respondieron **200**, y el worker creó su señal de disponibilidad. Coincidieron antes y después el resumen de calidad, el último ID de trabajo y las huellas de las primeras 2.000 filas de `raw_secop` y `contratos_procesados`, ordenadas por ID con zona UTC. Fuentes activas: **0**; trabajos activos: **0**.

No hubo recarga, normalización, migración ni copia de la base histórica. El resumen conservado contiene **9.249.545** contratos; no se repitió un conteo completo. Las pruebas autenticadas y el perfil de ocho lectores del 12/10 siguen siendo evidencia de aquella ejecución; esta recuperación comprueba disponibilidad y estado acotado. El primer intento del helper se detuvo al serializar un decimal del informe, antes de retirar el bloqueo; la ejecución corregida tiene su propio directorio de evidencia.

## Firewall: el acceso denegado no demuestra ausencia de reglas

Windows denegó la consulta del inventario efectivo con **System Error 5**. El proceso sigue sin elevación administrativa. No existen registros de ejecución/verificación del helper autorizado, pero no puede concluirse que no haya reglas en el sistema. Se corrigen las afirmaciones anteriores de «cero reglas nuevas» cuando procedían de una consulta que omitía errores; los snapshots privados anteriores se conservan.

`apply_local_egress.ps1` y el entrypoint administrativo ahora enumeran `ActiveStore` con `-ErrorAction Stop` antes de filtrar nombres. Cualquier error impide llegar a la creación de reglas. Se conserva `#Requires -RunAsAdministrator`, el límite de seis reglas y el rechazo a reglas existentes. Ambos scripts pasaron el análisis sintáctico de PowerShell; la consulta nativa estricta falló por permisos, como queda registrado. No se aplicaron reglas ni se cambiaron perfiles globales durante esta revisión.

La autorización humana ya está recibida. P01 requiere ejecución con privilegios de Windows y posterior prueba de tráfico real desde ambos Python. El comando preparado permanece en [la constancia de autorización](CONSERVACION_APROBADA_Y_EGRESO_20261012.md).

## Pendientes

**97/101 completados (96,0 %); cuatro pendientes:** P01 (firewall efectivo), P05 (identidad anterior al versionado), P06 (contraste con registro DIAN autorizado) y P12 (linaje de filas antiguas). Los tres últimos necesitan el registro autorizado y/o la extracción anterior con IDs oficiales. No se asignan identidades por semejanza de contenido.

[Evidencia estructurada y hashes](RECUPERACION_LOCAL_20261015.json). Todos los cambios se mantienen en este equipo.
