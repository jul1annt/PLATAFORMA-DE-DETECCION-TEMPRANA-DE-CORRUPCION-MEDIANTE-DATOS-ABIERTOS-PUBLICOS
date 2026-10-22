# Primer grupo completo evaluado con IQR corregido

## Resultado del desarrollo

Se implementó y ejecutó un evaluador descriptivo del corte con referencia completa por categoría, modalidad y año. El piloto utiliza categoría SECOP `V1.80161500`, modalidad `CONTRATACIÓN DIRECTA (CON OFERTAS)` y año de publicación 2017. Se eligió un grupo con identidades localizables en la exploración anterior, sin seleccionar por puntuación. Es un grupo piloto, no una muestra representativa de todas las modalidades o periodos.

La lectura recuperó todas las **1.698 filas** que coinciden con ese grupo, sin alcanzar el límite de 20.000. Después de comprobar identidad exacta en la fuente e importe positivo, quedaron **1.392 observaciones comparables identificadas** para la referencia. Son unidades de adjudicación; no son pares de reiteración ni expedientes judiciales.

| Resultado IQR en todas las filas del grupo | Cantidad |
| --- | ---: |
| Señal estadística detectada | 50 |
| Evaluable sin señal IQR | 1.342 |
| No evaluable | 306 |
| Puntaje completo de riesgo | **0** |

Las 306 no evaluables se conservaron con motivo: 299 con identidad incompleta, seis con identidad ambigua y una sin importe positivo válido. No se eliminaron de la base ni se les asignaron IDs nuevos. Las 1.392 unidades de referencia son aptas para este análisis descriptivo, **no** para entrenamiento judicial.

Las 50 señales expresan importes fuera de los límites del grupo. No constituyen 50 casos de corrupción ni acreditan sobreprecio. El campo de importe es el valor total adjudicado reportado por SECOP; no se confirmó moneda, escala y precio unitario con documentación física.

## Cómo se calcula y qué se conserva

`Backend/modules/motor_riesgo/cut_rules.py` valida que la entrada declare una cohorte completa, que cada fila pertenezca a su categoría/modalidad/periodo y que los objetivos estén incluidos. Se excluyen de la referencia las identidades ausentes, ambiguas o repetidas, importes inválidos y publicaciones posteriores al corte declarado. Se conservan adjudicaciones distintas y no se infieren identidades por nombres.

La referencia IQR exige 30 observaciones positivas identificables y dispersión positiva. Los cuartiles y límites se calculan **una sola vez** por grupo y se reutilizan para todos los objetivos. Se conserva hash de las unidades e importes empleados, del archivo adquirido y del código. Los valores de esta referencia fueron:

- Q1: `21.000.000`.
- Q3: `66.747.216`.
- Límite inferior: `−47.620.824`.
- Límite superior: `135.368.040`.

Son magnitudes del campo reportado, no precios unitarios verificados. El límite inferior negativo no permite inferir importes negativos: solo se admiten valores positivos al formar la referencia.

El primer ensayo desconectado evaluó tres objetivos tomados de la selección anterior. Después se evaluaron las 1.698 filas del grupo completo, incluidas las que deben abstenerse. Ambos recibos se conservan; el informe principal es [la evaluación completa](REGLAS_CORREGIDAS_COHORTE_COMPLETA_2017_20261019.json).

## Separación temporal y cobertura

Esta evaluación usa información disponible en el corte local actual. **No reconstruye lo que se sabía en 2017.** Su alcance es `current_cut_descriptive_not_stage_prediction`; cada resultado tiene `training_eligible=false`. La política de variables históricas rechaza ese alcance. Conservar una fecha de publicación antigua no convierte una captura actual en evidencia histórica de adjudicación.

No se reutilizó el máximo de riesgo de proveedor ni un par legado para fabricar conteos móviles. Competencia y concentración/reiteración permanecen sin evaluación cuando faltan sus requisitos. En esta modalidad concreta el diccionario conservador de competencia no declara un resultado conocido.

Por ello todas las filas conservan `complete_score=null`. En una fila con IQR evaluable y sin señal, el intervalo descriptivo de familias es `[0,2]`, no «riesgo bajo». Si IQR detecta señal, el intervalo es `[1,3]`. Las otras familias siguen desconocidas; estos intervalos no son probabilidades ni intervalos de confianza. La publicación y el índice del modelo permanecen deshabilitados.

## Lectura y rendimiento

La primera consulta completa agotó 30 segundos y se canceló. No se utilizó una respuesta parcial para calcular cuartiles. La adquisición final usó una transacción de solo lectura con cursor del servidor, bloques de 25 filas, límite de diez segundos por lectura y 16 MiB de memoria de trabajo. Tras finalizar el cursor se comprobaron identidades exactas con un máximo de dos coincidencias por unidad.

La adquisición y comprobación terminaron en **178,09 segundos**. El grupo completo se conserva para que el análisis no vuelva a consultar la base. La repetición desconectada de las 1.698 filas tardó aproximadamente **0,046 segundos** y produjo el mismo resultado. Los tiempos pertenecen a esta ejecución; no son una garantía ni una comparación controlada contra otras infraestructuras.

## Reproducción y validación

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_cut_cohort.py --input Backend/.codex-analytics-postgres/corrected-cohort-2017-all-targets.json --output cohorte-corregida-nueva.json
```

El comando es independiente de DB, API y bibliotecas de entrenamiento. Limita entrada a 16 MiB y 20.000 filas, conserva los objetivos no evaluables y no sobrescribe una salida existente. `tests/test_cut_rules.py` comprueba grupos incompletos, categorías y fechas incompatibles, IDs repetidos, cantidades inválidas, ausencia de dispersión, separación temporal, cálculo único de referencia y conservación del artefacto.

Pasaron **99 pruebas enfocadas**, que incluyen comprobaciones anteriores; no son 99 pruebas nuevas ni una nueva batería completa del backend. La [validación con hashes](VALIDACION_REGLAS_CORREGIDAS_COHORTE_2017_20261019.json) enlaza pruebas, fuente, referencia, código, repetición y lecturas de conservación del despliegue. La [política base v4](POLITICA_PESOS_BASE_V4.json) incorpora el piloto sin modificar coeficientes históricos.

El esquema operativo, los pesos **1 / 1,5 / 2**, la referencia publicada y el corte del **01/10/2026** permanecen intactos. El registro judicial no cambió. No hubo entrenamiento, contacto con terceros o publicación nueva.

## Siguiente paso

Construir conteos móviles de procesos distintos usando historial suficiente de entidad/proveedor y verificar la semántica de competencia. Deben mantenerse independientes la disponibilidad de contexto, la aplicabilidad de cada indicador y su resultado. Repetir después las comparaciones de sensibilidad sobre las familias corregidas y otros grupos completos. La validación judicial y la activación de modelos continúan siendo una fase posterior.
