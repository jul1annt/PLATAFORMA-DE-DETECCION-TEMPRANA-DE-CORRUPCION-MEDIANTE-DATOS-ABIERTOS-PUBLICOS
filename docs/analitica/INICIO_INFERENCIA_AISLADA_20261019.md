# Comprobación del intérprete antes del inicio

La revisión encontró que el inicio local validaba los modelos y permisos de base de datos sin ejecutar el intérprete configurado para la inferencia. Una ruta ausente, un entorno compartido con la API o un entorno incapaz de cargar la implementación podían detectarse recién durante la actualización diaria.

## Implementación

`scripts/risk_runtime_check.py` ahora ejecuta `scripts/risk_inference_probe.py` con el intérprete de la API seleccionado por el paquete y con `RISK_INFERENCE_PYTHON` de su configuración efectiva. Cada proceso usa `-I`, un límite de 30 segundos y el control existente del árbol de procesos. La comprobación importa la implementación predictiva del paquete; no entrena ni consulta contratos.

Para permitir el inicio, exige:

- Un ejecutable de inferencia configurado mediante ruta absoluta y existente.
- Carga correcta de la implementación y coincidencia de sus hashes predictivos con el paquete que valida la aprobación.
- Modo aislado de Python y ausencia de importaciones de scikit-learn, NumPy, SciPy, joblib y threadpoolctl.
- Un entorno virtual de inferencia cuyo `sys.prefix` difiera del intérprete base y del entorno efectivo de la API. Se comparan los prefijos informados por los procesos, no solo nombres de ejecutables.

Los procesos de comprobación reciben únicamente variables del sistema operativo necesarias para su ejecución y límites de hilos. No se les transfieren variables de base de datos, claves ni configuración del modelo. La actualización diaria no depende de iniciar el entorno de entrenamiento.

Esta comprobación acredita que las dependencias de entrenamiento no se importan al cargar la inferencia; no declara que esas bibliotecas estén desinstaladas. Tampoco sustituye una ejecución completa de inferencia con modelos reales aprobados.

## Validación

La ejecución focalizada pasó 33 pruebas: 16 de esta comprobación y 17 de permisos. Incluye la ejecución real con el entorno independiente de inferencia y el rechazo real de reutilizar el intérprete de la API. Los demás casos simulan respuestas incompatibles, fallo del proceso, ausencia de ruta, hashes diferentes y carga indebida de dependencias.

La batería completa terminó con **707 pruebas aprobadas**, cero fallos, errores u omisiones, en 68,33 segundos. El [resultado consolidado](VALIDACION_INICIO_INFERENCIA_20261019.json) conserva los hashes del código y de los registros. No se instaló una tarea, no se inició el supervisor y no se activó el índice.
