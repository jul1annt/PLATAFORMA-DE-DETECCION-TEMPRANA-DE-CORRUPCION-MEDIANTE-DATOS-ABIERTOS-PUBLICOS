# Control de los procesos analíticos locales

## Propiedad y cierre en Windows

El ejecutable de un entorno virtual puede lanzar otro Python. El comando empieza suspendido; la API lo asigna mediante su handle de `Popen` a un Job Object privado y después reanuda su único hilo inicial. Así se evita que aparezca un descendiente antes de establecer la propiedad. Un fallo de asignación detiene el hijo suspendido y rechaza ejecutar sin contención.

El job usa `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, sin nombre, permiso de escape ni handle heredable. Windows cierra el árbol cuando desaparece su propietario, aunque Python no alcance un `finally`. Un tiempo máximo lo termina expresamente. Esta semántica y la pertenencia de los descendientes están descritas por [Microsoft: Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

La implementación utiliza la biblioteca estándar y el handle de CPython Windows. El equipo actual admite jobs anidados; una plataforma incompatible debe fallar antes de ejecutar el comando. En POSIX se conserva una sesión privada y su cierre por tiempo máximo: no se afirma que la muerte del propietario tenga la misma garantía automática.

## Independencia del modelo

El registro `.process.execution.json` conserva estado observado, límite, hilos y hashes del ejecutable y del código de control. No contiene el entorno ni sus credenciales. `service.py`, `process_runner.py` y `windows_job.py` se versionan en ese registro, separados del manifiesto de aprobación predictiva. Los coeficientes y su inferencia portable no dependen de esas piezas de la API.

Un registro `RUNNING` sin cierre es la última observación, no prueba de que el proceso siga vivo. La recuperación durable utiliza el estado de PostgreSQL y su bloqueo de sesión; no toma esa anotación como una señal de vida.

## Evidencia local

- [Job Windows, revisión final](VALIDACION_WINDOWS_JOB_REV2_20261016.json): árboles sintéticos en el intérprete real de inferencia. Tiempo máximo: 5,13 s. Salida abrupta del supervisor: 1,83 s; sus descendientes terminaron. El informe conserva hashes del código ensayado.
- [Recuperación del worker](VALIDACION_RECUPERACION_WORKER_20261016.json): base vacía OID 82244, rol ordinario. Un trabajo sintético de entrenamiento pasó a `EN_PROCESO`; su propietario salió abruptamente y sus hijos terminaron. El worker recuperó el mismo UUID a `PENDIENTE` y después a `EXITOSO`, en dos intentos y sin duplicar la tarea. Solo se retiró el trabajo ficticio identificado; fuentes y modelos quedaron intactos.
- La suite completa incorpora rechazo de fallos al crear/asignar jobs, cierre de handles, límites de tiempo, protección de registros y separación del manifiesto predictivo.

Estas pruebas no entrenan modelos, no publican índices y no sustituyen el ensayo del servidor HTTP y paquete operativo final con modelos aprobados. La [prueba anterior de cierre por plazo](VALIDACION_CIERRE_PROCESOS_20261016.json) se conserva como antecedente de la revisión previa.
