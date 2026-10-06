# Integración en este equipo

Entorno autorizado por el usuario el 2026-10-06. La preparación y sus comprobaciones están en curso; este documento describe el control del entorno, no acredita todavía el cierre de P01, P02, P10 o P18.

## Componentes y datos

- Interfaz compilada: `http://127.0.0.1:4173`.
- API: `http://127.0.0.1:8000`.
- Worker dedicado con la misma versión del backend.
- PostgreSQL aislado en `127.0.0.1:5433`, base `plataforma_integracion_local`, rol ordinario `plataforma_integracion`.
- Copia del corte histórico conservado de 9 249 545 registros. Las fuentes quedan deshabilitadas, sus claves eliminadas de la copia y los administradores heredados desactivados. El corte no se presenta como actualización de la fuente oficial.

La base operativa en `:5432`, las generaciones fuente y sus respaldos se conservan. Esta integración persistente utiliza una copia propia para sus sesiones, trabajos y exportaciones.

## Archivos privados

El directorio `Backend/.codex-integration-postgres/`, excluido de Git, guarda versiones, Python propio, configuración, credenciales, exportaciones y logs. Su ACL permite acceso al usuario de despliegue, SYSTEM y Administradores. No copiar su contenido en incidencias o mensajes. La contraseña de `admin_local` está en `acceso-local.txt` dentro de ese directorio.

El controlador comprueba destino, versión de dependencias, ejecutable Python, versión de interfaz y hashes de sus archivos. Sirve únicamente el bundle, con protección de rutas; las credenciales no pertenecen al directorio publicado. Los procesos se registran con PID y fecha de creación para evitar confundir un PID reutilizado con un servicio propio.

## Inicio, consulta y cierre

Desde la raíz del proyecto, con el PostgreSQL aislado disponible:

```powershell
$integracion = Join-Path (Get-Location) 'Backend/.codex-integration-postgres'
$pythonIntegracion = Join-Path $integracion 'runtime/venv/Scripts/python.exe'
& $pythonIntegracion Backend/scripts/local_integration.py status
& $pythonIntegracion Backend/scripts/local_integration.py start
& $pythonIntegracion Backend/scripts/local_integration.py status
```

Abrir la interfaz cuando el estado sea `running` y los tres componentes estén activos. Los servicios solo escuchan en este equipo. El supervisor cierra los demás componentes si alguno termina inesperadamente y no introduce un ciclo de reinicios.

Para detener:

```powershell
& $pythonIntegracion Backend/scripts/local_integration.py stop
& $pythonIntegracion Backend/scripts/local_integration.py status
```

El cierre se rechaza si hay trabajos activos. Los componentes cierran sus conexiones y el worker espera sus tareas antes de terminar. Esperar estado `stopped` y procesos inactivos antes de cambiar la versión. Un bloqueo de una ejecución anterior exige comprobar la identidad y ausencia de sus procesos; no borrar el bloqueo mientras haya componentes vivos.

Después de reiniciar Windows, PostgreSQL debe iniciarse con el directorio del clúster aislado y opciones explícitas `-p 5433 -h 127.0.0.1`; su configuración heredada no determina el puerto de esta integración. No detener otro clúster para liberar un puerto ocupado.

## Reversa y recuperación

La reversa cambia artefactos después de cerrar los servicios y verificar compatibilidad con la revisión Alembic de la base. No ejecutar un downgrade de esquema rutinario. Conservar las credenciales y cola de esta integración durante el cambio. El ensayo debe registrar versiones, hashes, estado de cola, revisión, consultas y exportaciones antes y después.

El dump histórico verificado permite recuperar el corte de origen; no contiene las sesiones ni los trabajos creados posteriormente en la integración. La recuperación debe respaldar o reconciliar también ese estado local antes de declarar restauración completa. Véase `docs/auditoria/GUIA_DESPLIEGUE_Y_REVERSA.md`.

## Egreso del proceso

`Backend/scripts/prepare_local_egress.py` prepara seis reglas para los dos ejecutables de Python propios de esta integración. `apply_local_egress.ps1` requiere una sesión administradora y comprueba rutas, hashes, antigüedad de la resolución y ausencia de reglas con los mismos nombres antes de aplicarlas. No modifica perfiles globales ni reglas de otros programas.

Las reglas bloquean TCP externo salvo HTTPS hacia las IP públicas resueltas de `www.datos.gov.co` y `datos.gov.co`, y bloquean UDP externo del proceso. Las conexiones TCP locales de API/base permanecen disponibles. La resolución normal de nombres usa el servicio de Windows. El bloqueo de HTTPS es el complemento de las direcciones aprobadas: no depende de una regla de permitir que pueda ser anulada por otra de bloqueo. La política de URLs de la aplicación sigue verificando HTTPS, puerto, nombre, DNS público, redirecciones y credenciales.

La lista es una instantánea de DNS, no una autorización permanente por nombre: revisar y sustituir únicamente estas reglas cuando cambien las IP de las fuentes. La preparación expira para aplicación a los 30 minutos. La [documentación de Microsoft](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps) describe el alcance por programa, protocolo y destino; las [reglas de precedencia](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules) explican la prioridad de bloqueos.

En el intento del 2026-10-06, la elevación terminó con `InvalidOperationException`; no se confirmó aplicación de reglas. La comprobación previa accedió por HTTPS a SECOP y también al destino público no aprobado del ensayo. P01 requiere aplicación y prueba posterior de bloqueo; no queda cerrado por preparar estos archivos.
