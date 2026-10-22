# Admisión explícita de la base monetaria

## Carencia encontrada y corrección

La resolución original 641 de Ruta del Sol expresa un VPIT en pesos del 31/12/2008, mientras la ficha actual presenta el mismo número como cuantía contractual. El registro de evidencia anterior verificaba integridad, revisión de valores y fechas, sin exigir declarar esa diferencia semántica.

`analytics_ml/evidence.py` añade la política **`reviewed-physical-stage-evidence-v2`**. Para cada importe no nulo, exige revisión de base monetaria, importe decimal original, moneda COP, unidad pesos, base nominal, significado presupuesto o adjudicación según el campo y transformación LOG1P coherente. La revisión del campo incluye hash de esos metadatos y localizador documental de sus unidades y significado.

Un VPIT, una cantidad en pesos constantes, millones o moneda extranjera no entra mediante una conversión implícita. La corrección no incorpora deflactores ni tasas de cambio. Omitir un importe conserva la posibilidad de registrar otros campos válidos; la ausencia de variables esenciales produce abstención del modelo.

## Separación y compatibilidad

La validación se ejecuta al registrar evidencias, al preparar el entrenamiento y al recuperar observaciones para inferencia por lotes. La aprobación compartida exige la nueva política de evidencia en el informe enlazado al artefacto. Los informes de política v1 no acreditan la revisión v2.

El cálculo predictivo `secop-point-in-time-v3` mantiene su fórmula y lista de variables. La modificación afecta la admisión de evidencia. No se añadió dependencia externa, migración o entrenamiento a la API. El manifiesto de entrenamiento ya incluye el hash de `evidence.py`, y el informe incluye la política y el hash del registro revisado.

El [protocolo actualizado](EVIDENCIAS_VARIABLES.md) documenta la estructura y un ejemplo sintético. No hay revisiones reales registradas que se hayan convertido automáticamente al formato nuevo.

## Validación y límites

Se añadieron **43 pruebas sintéticas** para ambas etapas: declaraciones ausentes, moneda, pesos constantes, VPIT, millones, significado invertido, transformación, integridad, localizadores, importes inválidos y ausencia selectiva de campos. La suite existente comprueba persistencia y equivalencia de los valores entre entrenamiento e inferencia con evidencias válidas.

La primera ejecución específica pasó 111 pruebas y falló una: su preparación alteraba un logaritmo sin actualizar el importe original. El validador rechazó correctamente esa incoherencia. Se corrigió la preparación para conservar dos revisiones válidas pero contradictorias, que siguen provocando abstención. La repetición pasó **113 pruebas** y la suite completa pasó **656 pruebas en 69,52 segundos**, sin fallos, errores u omisiones. Sus registros son `3985c7a9348341fdbae7eebb038ec3f4`, `b574ec8e29ad48e597c69739ca37e670` y `04bcedc7a2384aa89492c349419da8fe`, respectivamente.

La [validación consolidada](VALIDACION_BASE_MONETARIA_20261019.json) preserva hashes de código y JUnit. Comprobó por lectura la base aislada vacía después de las pruebas y el esquema original `3c19a8f7e2d0`, sin tablas nuevas de publicación analítica. No se repitieron cargas masivas ni migraciones.

La [consulta oficial acotada de SECOP](CORRESPONDENCIA_SECOP_RUTA_SOL_20261019.md) no corroboró el ID candidato del proceso antiguo. Esta corrección no admite el caso Ruta del Sol, no aumenta el número de positivos y no entrena o publica modelos reales.
