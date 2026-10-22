# Autoinicio desde el paquete seleccionado

El instalador de la tarea Windows suponía que Python estaba en `Backend/venv`. Ese directorio existe en el entorno de desarrollo, pero no en el paquete preparado, que conserva su runtime separado. Además, el instalador elegía el control de aprobación y el controlador junto al script que se invocaba, aunque el manifiesto seleccionara otro backend.

## Corrección

`install_risk_autostart.ps1` ahora obtiene Python de `runtime.json` y el backend de `release.json`. Comprueba las rutas absolutas bajo los directorios esperados y selecciona desde ese backend el control de aprobación, el controlador y el instalador que se guardará en la acción de la tarea. Ejecutar el instalador desde el árbol de desarrollo ya no hace que la tarea quede vinculada a esa copia.

El control de aprobación sigue ejecutándose antes de consultar o registrar tareas y antes de iniciar servicios. Se mantienen el usuario interactivo con privilegios limitados, la recuperación al estar disponible, la exclusión de ejecuciones simultáneas y el rechazo de reemplazar una tarea existente.

## Verificación

Se añadieron 13 pruebas ejecutadas en Windows PowerShell. Los comandos del Programador de tareas están sustituidos por funciones de simulación en esos procesos de prueba: ninguna prueba registra una tarea real. Comprueban:

- Rechazo de los modos de instalación y ejecución cuando falla la aprobación, sin consultar tareas ni iniciar servicios.
- Uso del runtime, controlador e instalador seleccionados, con rutas que contienen espacios.
- Inicio solicitado solo cuando no existe un supervisor activo.
- Construcción de la acción, principal y opciones de la tarea; rechazo de una tarea existente.
- Rechazo temprano de rutas externas, relativas, archivos ausentes y manifiesto de runtime ausente.

En el paquete real inactivo se ejecutaron además los dos modos del instalador: ambos llegaron al control de modelos y fueron rechazados por ausencia de modelos aprobados. El backend del paquete no contiene un directorio `venv`; el rechazo correcto demuestra que se utilizó el runtime declarado y se alcanzó el control previsto. Los manifiestos y el estado detenido permanecieron iguales.

La revisión 3 del paquete conserva la revisión 2, que ya había pasado los dos ciclos nativos de inicio y parada. Solo cambió el instalador PowerShell: el controlador, runtime, código de API e interfaz son iguales. No se repitieron aquellos ciclos como si fueran una validación nueva de esta revisión. Se comprobó específicamente el instalador empaquetado corregido.

La batería completa terminó con **744 pruebas aprobadas**, cero fallos, errores u omisiones, en 76,29 segundos. La [evidencia consolidada](VALIDACION_AUTOINICIO_PAQUETE_20261019.json) conserva hashes de código, registros y revisión del paquete.

## Límite de aceptación

La rama positiva de registro y arranque está probada mediante simulaciones. No se instaló una tarea Windows, no se ejecutó el disparador mediante un inicio de sesión real y no se aprobó un modelo. Esa aceptación operativa sigue condicionada a la evidencia judicial e histórica, evaluación de ambos modelos y superación de los criterios de publicación ya acordados.
