# Integración en este equipo

Entorno autorizado por el usuario el 2026-10-06. API, interfaz compilada y worker dedicado quedaron activos. [El ensayo documentado](../auditoria/INTEGRACION_LOCAL_20261006.md) cierra P02, P10 y P18 para este equipo; P01 conserva la aplicación y comprobación del cortafuegos pendientes.

## Componentes y datos

- Interfaz compilada: `http://127.0.0.1:4173`.
- API: `http://127.0.0.1:8000`.
- Worker dedicado con la misma versión del backend.
- PostgreSQL operativo en `127.0.0.1:5432`, base `plataformaanticorrupcion`, OID 24577, rol ordinario `plataforma_operacion`. La integración anterior de :5433 se conserva para recuperación.
- Copia del corte histórico conservado de 9 249 545 registros. Las fuentes quedan deshabilitadas, sus claves eliminadas de la copia y los administradores heredados desactivados. El corte no se presenta como actualización de la fuente oficial.

El 2026-10-10 UTC se publicó el histórico aceptado en la base operativa. El original conserva 18 980 filas bajo `plataformaanticorrupcion_pre_20261010`, OID 17930; las generaciones fuente y sus respaldos únicos permanecen. [Publicación y controles](../auditoria/PUBLICACION_CORTE_HISTORICO_20261010.md).

## Archivos privados

El directorio `Backend/.codex-integration-postgres/`, excluido de Git, guarda versiones, Python propio, configuración, credenciales, exportaciones y logs. Su ACL permite acceso al usuario de despliegue, SYSTEM y Administradores. No copiar su contenido en incidencias o mensajes. La contraseña de `admin_local` está en `acceso-local.txt` dentro de ese directorio.

El controlador comprueba destino, versión de dependencias, ejecutable Python, versión de interfaz y hashes de sus archivos. Sirve únicamente el bundle, con protección de rutas; las credenciales no pertenecen al directorio publicado. Los procesos se registran con PID y fecha de creación para evitar confundir un PID reutilizado con un servicio propio.

Versión backend/worker aplicada con la publicación del 2026-10-10 UTC: `915e863cc7492e619888506f59a04c6dbbfa5552`; interfaz conservada de `9362d94f9dbfbdf352ae11585a2bfd44318b11e6` tras cotejar su árbol completo y hashes. Revisión PostgreSQL `f4826b9d1c30`, 20 índices válidos. La interfaz muestra el corte del 01/10/2026 mediante `VITE_DATA_CONTEXT`; ese texto acompaña los conteos de la API y no certifica una actualización oficial. El backend concentra conteos, clasificación y ranking; React muestra sus resultados y evita superponer el refresco del tablero. [La actualización de métricas](../auditoria/OPTIMIZACION_METRICAS_20261009.md) conserva los resultados y declara sus límites de rendimiento. El manifiesto de `83382f9` anterior a esta publicación queda en `publication-20261010/control-checkpoint/release.json`. `metrics-release-previous-20261009.json` conserva la reversa del despliegue de métricas anterior. Volver a un backend compatible no exige downgrade rutinario de esquema.

## Inicio, consulta y cierre

Desde la raíz del proyecto, con el PostgreSQL operativo :5432 disponible:

```powershell
$integracion = Join-Path (Get-Location) 'Backend/.codex-integration-postgres'
$pythonIntegracion = Join-Path $integracion 'runtime/venv/Scripts/python.exe'
& $pythonIntegracion Backend/scripts/local_integration.py --root $integracion status
& $pythonIntegracion Backend/scripts/local_integration.py --root $integracion start
& $pythonIntegracion Backend/scripts/local_integration.py --root $integracion status
```

Abrir la interfaz cuando el estado sea `running` y los tres componentes estén activos. Los servicios solo escuchan en este equipo. El supervisor cierra los demás componentes si alguno termina inesperadamente y no introduce un ciclo de reinicios.

Para detener:

```powershell
& $pythonIntegracion Backend/scripts/local_integration.py --root $integracion stop
& $pythonIntegracion Backend/scripts/local_integration.py --root $integracion status
```

El cierre se rechaza si hay trabajos activos. Los componentes cierran sus conexiones y el worker espera sus tareas antes de terminar. Esperar estado `stopped` y procesos inactivos antes de cambiar la versión. Un bloqueo de una ejecución anterior exige comprobar la identidad y ausencia de sus procesos; no borrar el bloqueo mientras haya componentes vivos.

Después de reiniciar Windows, comprobar el clúster operativo :5432 y su directorio `C:/Users/Julianxxo/AppData/Local/PostgreSQL/15/data` antes de iniciar los servicios. El clúster anterior :5433 conserva `recovery-clone-20260929` y exige opciones explícitas `-p 5433 -h 127.0.0.1` si se necesita para recuperación. No detener otro clúster para liberar un puerto ocupado.

## Reversa y recuperación

La publicación actual añade `publication-20261010/control-checkpoint/`: estado de las cuatro tablas de control, configuración y exportaciones justo antes del cambio. La recuperación completa debe combinar el histórico con ese estado posterior y reconciliar escrituras nuevas. Si el destino no usa `Spanish_Argentina.1252`, aplicar [el SQL de locale](PRESERVAR_LOCALE_SECOP_20261001.sql) solo con las identidades declaradas; preferir crear una restauración nueva con UTF8 y el locale de origen desde el principio.

La reversa cambia artefactos después de cerrar los servicios y verificar compatibilidad con la revisión Alembic de la base. No ejecutar un downgrade de esquema rutinario. Conservar las credenciales y cola de esta integración durante el cambio. El ensayo debe registrar versiones, hashes, estado de cola, revisión, consultas y exportaciones antes y después.

El dump histórico verificado permite recuperar el corte de origen; no contiene las sesiones ni los trabajos creados posteriormente en la integración. `recovery-state-final/` conserva un checkpoint privado posterior con configuración, credenciales, exportaciones y dump de las cuatro tablas de control. Su restauración independiente, login/logout, secuencias y reposición real del acceso local pasaron. `state-recovery-final.json` registra huellas y alcance. Véase [la guía de despliegue y reversa](../auditoria/GUIA_DESPLIEGUE_Y_REVERSA.md).

Para recuperar desde la base histórica, mantener los servicios cerrados, aplicar las migraciones del artefacto actual y reponer el checkpoint de control **por claves**, respetando las referencias a fuente y administrador. No vaciar `fuentes_datos` con `CASCADE`: los contratos conservan referencias a esa fuente. Alinear las secuencias por encima de los IDs recuperados, verificar huellas de tablas y archivos y reconciliar cualquier escritura posterior al checkpoint antes de abrir el servicio. El ensayo actual repuso filas desde la restauración independiente sin borrar ni volver a transformar los contratos. La restauración de nueve millones ya comprobada el 03/10 se reutilizó como evidencia de la capa base.

La reversa ensayada volvió a `0c065c4e034c` y después a `9362d94f9dbf`, cambiando tanto `release.json` como el manifiesto del bundle correspondiente, con los tres procesos detenidos. El esquema aditivo quedó en la revisión actual; el código anterior se ejecutó sin invocar su Alembic. Conservar ambos artefactos, manifiestos y el respaldo; no usar para reversa el backend `a039e2f`, cuyo Mako fue rechazado por la auditoría.

## Egreso del proceso

`Backend/scripts/prepare_local_egress.py` prepara seis reglas para los dos ejecutables de Python propios de esta integración. `apply_local_egress.ps1` requiere una sesión administradora y comprueba rutas, hashes, antigüedad de la resolución y ausencia de reglas con los mismos nombres antes de aplicarlas. No modifica perfiles globales ni reglas de otros programas.

Las reglas bloquean TCP externo salvo HTTPS hacia las IP públicas resueltas de `www.datos.gov.co` y `datos.gov.co`, y bloquean UDP externo del proceso. Las conexiones TCP locales de API/base permanecen disponibles. La resolución normal de nombres usa el servicio de Windows. El bloqueo de HTTPS es el complemento de las direcciones aprobadas: no depende de una regla de permitir que pueda ser anulada por otra de bloqueo. La política de URLs de la aplicación sigue verificando HTTPS, puerto, nombre, DNS público, redirecciones y credenciales.

La lista es una instantánea de DNS, no una autorización permanente por nombre: revisar y sustituir únicamente estas reglas cuando cambien las IP de las fuentes. La preparación expira para aplicación a los 30 minutos. La [documentación de Microsoft](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps) describe el alcance por programa, protocolo y destino; las [reglas de precedencia](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules) explican la prioridad de bloqueos.

En el intento del 2026-10-06, la elevación terminó con `InvalidOperationException`; no se confirmó aplicación de reglas. La comprobación previa accedió por HTTPS a SECOP y también al destino público no aprobado del ensayo. P01 requiere aplicación y prueba posterior de bloqueo; no queda cerrado por preparar estos archivos.

Para el paso pendiente, abrir PowerShell **como administrador**, ubicarse en la raíz del proyecto y resolver de nuevo las direcciones justo antes de aplicar:

```powershell
$integracion = Join-Path (Get-Location) 'Backend/.codex-integration-postgres'
$pythonIntegracion = Join-Path $integracion 'runtime/venv/Scripts/python.exe'
& $pythonIntegracion Backend/scripts/prepare_local_egress.py --root $integracion
& Backend/scripts/apply_local_egress.ps1 -IntegrationRoot $integracion
```

Después comprobar desde ese Python dedicado el destino no aprobado bloqueado, HTTPS oficial accesible y PostgreSQL local disponible. `egress-applied.json` registra aplicación; no sustituye la comprobación de conectividad. El requerimiento de administrador lo impone `#Requires -RunAsAdministrator` y la administración del cortafuegos de Windows; esta sesión no dispone de esa elevación.
