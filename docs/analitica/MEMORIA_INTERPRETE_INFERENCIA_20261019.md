# Memoria del intérprete efectivo de inferencia

Se completó la medición pendiente del proceso que realmente ejecuta la inferencia. Los ensayos anteriores que medían el lanzador de un entorno virtual Windows no acreditaban la memoria de su intérprete descendiente.

## Método

Se ejecutó el CLI existente `scripts/risk_process.py infer`, sin modificarlo, dentro del entorno independiente de inferencia. Un envoltorio local instrumentado llamó a `GetProcessMemoryInfo(GetCurrentProcess())` al terminar, recuperando el pico de working set que Windows conserva para toda la vida del proceso. `GetModuleFileNameW` confirmó la imagen real de Python; el informe conserva por separado su PID, el del padre y el del supervisor.

La medición incluye el intérprete, las dos referencias sintéticas, lectura y escritura gzip y la instrumentación. No incluye la memoria total del sistema, PostgreSQL, API, lectores HTTP o del supervisor. El entorno efectivo no tenía `sklearn` ni `numpy` instalados.

Se utilizaron dos artefactos sintéticos de 25 miembros y datos identificados como sintéticos, con ambas etapas intercaladas. No se entrenaron modelos, no se accedió a bases de datos ni se publicaron resultados. Los artefactos carecen de evaluación judicial aprobada.

## Resultados

| Observaciones totales | Por etapa | Tiempo dentro del intérprete | Pico de working set |
| ---: | ---: | ---: | ---: |
| 2.000 | 1.000 | 0,322 s | 20.873.216 bytes, 19,91 MiB |
| 100.000 | 50.000 | 11,773 s | 20.926.464 bytes, 19,96 MiB |

Todas las observaciones recibieron índice, comprobado contra `evaluated_counts` y la lectura de resultados. El incremento entre ensayos fue **53.248 bytes, 52 KiB**. Los primeros 2.000 resultados fueron idénticos byte por byte en ambos tamaños, comparando el contenido descomprimido.

Esta comparación describe estos dos ensayos, con vocabularios y artefactos pequeños. No prueba un límite universal de memoria ni permite extrapolar sin medir el tamaño de referencias, categorías o modelos reales.

## Evidencia conservada y pendiente

El [informe de ejecución](MEMORIA_INTERPRETE_INFERENCIA_20261019.json) conserva métricas, identidades y muestras. La [verificación posterior](VALIDACION_MEMORIA_INFERENCIA_20261019.json) comprueba los hashes de archivos, manifiestos, código predictivo, dependencias y modelos, además de la igualdad del prefijo. Los archivos comprimidos y los artefactos se conservan en el directorio aislado del ensayo.

Para reproducir, revisar primero los scripts `Backend/.codex-e2e-postgres/measure_actual_inference_20261019.py` e `inference_memory_child_20261019.py`. El ejecutor crea exclusivamente un directorio nuevo y utiliza `bounded_run`, con el Job Object de Windows ya validado y un plazo de 240 segundos por ensayo. No sobrescribe una ejecución previa.

Se cierra la carencia de medición del **intérprete real para el flujo sintético evaluado**. Permanecen pendientes los recursos del despliegue completo con modelos judiciales aprobados y lecturas concurrentes. No se repitieron las cargas masivas anteriores ni las 656 pruebas del backend, porque no cambió el código de producción.
