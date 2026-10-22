# Ensayo del paquete aislado

Se preparó un paquete privado con el backend del árbol de trabajo, una copia del runtime de API con las mismas dependencias bloqueadas y una compilación nueva de la interfaz. El manifiesto identifica cada archivo por hash; su backend coincide con el código que pasó la batería de pruebas. No es una versión publicada ni un conjunto de modelos judiciales aprobado.

## Cambios necesarios

El supervisor usaba los puertos 8000 y 4173 directamente, tanto para enlazar servicios como para comprobar disponibilidad. Ahora emplea los puertos del manifiesto de la versión y exige direcciones HTTP explícitas en `127.0.0.1`, distintas para API e interfaz. La versión publicada sigue declarando sus puertos originales. La aceptación usa 18100 y 14173 junto con la base aislada OID 82244, cuyo nombre, puerto, rol, OID y revisión se comprueban antes de operar.

El primer ensayo completó un ciclo de inicio y parada, pero falló al reiniciar. Windows rechazó el reemplazo atómico de `services.json` durante una lectura concurrente. Se conservan el paquete y el fallo originales. La escritura de estado ahora utiliza un temporal propio y hasta veinte intentos ante `PermissionError`, separados por 50 ms; otros errores no se reintentan. No se trunca el estado anterior. La liberación de archivos y del bloqueo también ocurre si falla el registro final del estado.

## Comprobaciones realizadas

La segunda versión completó **dos ciclos de inicio y parada** de API, interfaz y worker:

- Consultas HTTP a OpenAPI y las rutas públicas de estado, metodología y resultados.
- Servicio de la ruta de acceso administrativo de la interfaz y CORS para el origen aislado.
- Rechazo de entrenamiento sin autenticación; inicio de sesión con una cuenta temporal, consultas administrativas autorizadas y revocación de acceso después del logout.
- Rechazo de activación sin modelos aprobados mediante HTTP 409 y rechazo por la comprobación de inicio analítico.
- Recuperación de un trabajo sintético abandonado: conserva el mismo identificador, pasa del intento 1 al 2 y termina en error por ausencia de modelos. El segundo arranque no lo duplica ni lo ejecuta de nuevo.
- Cierre de todos los procesos del ensayo, retirada de la cuenta y sesiones temporales y eliminación exclusiva del trabajo de prueba identificado.

La batería completa del backend terminó con **731 pruebas aprobadas**, cero fallos, errores u omisiones. Las pruebas focalizadas cubren direcciones, identidad aislada, conflictos transitorios de escritura, denegaciones permanentes y conservación del estado previo.

Los hashes de configuración publicados permanecieron iguales. La API publicada y la interfaz original respondieron HTTP 200 en las comprobaciones de lectura. Este ensayo no realizó una nueva auditoría integral de sus bases de datos ni cambió sus versiones.

La [evidencia estructurada](VALIDACION_PAQUETE_AISLADO_20261019.json) conserva hashes, versión, resultados y límites. El primer informe interno dejó su campo de estado en `RUNNING` al fallar; no se considera una ejecución viva ni aprobada: el proceso terminó con error, el estado del supervisor documenta `PermissionError` y sus procesos quedaron detenidos. El registrador del ensayo se corrigió para identificar futuros fallos explícitamente.

## Pendientes

No se crearon datos de modelos ni se activó la publicación. El ensayo acredita el comportamiento del paquete sin modelos aprobados. Siguen pendientes la suficiencia judicial e histórica, entrenamiento y evaluación reales, recursos y recuperación/reversa con los modelos aprobados, autoinicio Windows y revisión visual del paquete final. El servicio de HTML no sustituye una revisión visual en navegador.
