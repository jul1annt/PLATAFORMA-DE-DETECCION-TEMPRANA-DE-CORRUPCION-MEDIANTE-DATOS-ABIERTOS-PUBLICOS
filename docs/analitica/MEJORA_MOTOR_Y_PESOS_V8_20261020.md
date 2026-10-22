# Motor y pesos v8: prioridades con cobertura y sensibilidad

## Cambio implementado

La [política v8](POLITICA_PESOS_BASE_V8.json) incorpora priorización descriptiva por operación al motor candidato. Usa las reglas corregidas y los resultados de las investigaciones y evaluaciones anteriores. La [aceptación de la base](ACEPTACION_BASE_MOTOR_20261020.md) y el informe general del 20/10 describen la versión anterior; esta mejora es posterior y conserva sus evidencias.

El problema abordado es concreto: ordenar por el conteo parcial de señales puede relegar operaciones que carecen de datos; cambiar pesos sin tratar cobertura o escala puede aparentar una mejora sin acreditarla. El censo legado de 31.731 resultados ya mostró dominancia de escala IQR. La composición nueva de 1.698 objetivos mostró competencia desconocida en todos ellos y muchas historias faltantes. No se eligen coeficientes óptimos a partir de esos vacíos.

## Política de pesos y evidencia

- El motor corregido conserva un máximo de **un punto por familia**. Las magnitudes extremas del IQR no se trasladan a la suma de familias. Directas y reiteración dentro de la misma familia no se duplican.
- Se evalúa la sensibilidad de **todos los pesos simultáneamente entre 0,80 y 1,20** alrededor de la referencia 1/1/1. Es una decisión de ingeniería documentada, no un intervalo estadístico ni calibración judicial.
- Una familia detectada aporta su peso; una familia sin señal aporta cero; una familia desconocida conserva el intervalo `[0, peso]`. Inaplicabilidad se mantiene separada.
- Para afirmar prioridad entre dos operaciones, la cota inferior de una debe superar la cota superior de la otra para todos los pesos considerados. No se asigna precedencia por ID, nombre o dato ausente.
- Solo se comparan operaciones de la misma cohorte, etapa y conjunto de familias aplicables. No se mezclan resultados de convocatoria con adjudicación, ni marcos de referencia distintos.
- Se conservan estados y detalle por indicador. Una familia OR confirmada puede contener otro indicador sin evidencia; eso no desaparece detrás del conteo completo de familias.

La comparación de cotas utiliza diferencias lineales. Sus extremos dentro de la caja de pesos se encuentran en los vértices; se comprueban ocho cuando hay tres familias aplicables. Así la garantía cubre también los pesos interiores, no solo ocho escenarios aislados. Los límites de posición agregados son conservadores: no se afirma que todos puedan alcanzarse simultáneamente.

## Salidas nuevas

Cada operación conserva:

| Campo | Significado |
| --- | --- |
| `confirmed_families` / `unknown_families` | Señales confirmadas y familias pendientes de evidencia |
| `central_weighted_count_interval` | Conteo mínimo y máximo bajo pesos centrales; no probabilidad |
| `comparison_group` / `comparison_population` | Alcance exacto de la comparación |
| `best_rank_bound` / `worst_rank_bound` | Límites conservadores de posición, incluyendo empates y datos faltantes |
| `strictly_lower_priority_guaranteed` | Cuántas operaciones quedan detrás bajo todas las condiciones consideradas |
| `priority_is_fully_resolved` | Si los límites de posición coinciden en ese grupo; no significa clasificación de corrupción |
| `review_route` | Revisar señales confirmadas, completar evidencia o conservar ausencia de señales observadas |
| `incomplete_indicator_evidence` | Falta evidencia de al menos un indicador aplicable, incluso con familia OR determinada |

Las rutas de revisión no son niveles bajo/medio/alto. Una operación con señal confirmada puede seguir necesitando datos: las familias desconocidas se conservan en su detalle. `SIN_SENAL_OBSERVADA` exige familias aplicables determinadas; tampoco acredita ausencia de corrupción.

Ejemplo: una operación con señal confirmada puede preceder de forma sólida a otra completamente evaluada sin señales. Si la segunda tiene familias desconocidas, esa precedencia puede dejar de ser demostrable. La salida conserva esa incertidumbre.

## Integración y separación de dependencias

`Backend/modules/motor_riesgo/robust_priority.py` contiene el dominio puro. `joint_baseline.py` añade `priority` a cada operación y `priority_analysis` al informe de composición. El CLI existente `risk_joint_baseline.py` registra el nuevo módulo en su manifiesto. La metodología pública candidata expone la política v8 y el alcance de sensibilidad.

`Backend/scripts/risk_robust_priority.py` permite evaluar informes de composición guardados sin conectarse a PostgreSQL, entrenar ni cargar bibliotecas externas. Rechaza sobrescribir entradas o salidas, JSON con claves repetidas, ámbitos incompatibles, identidades duplicadas, cobertura alterada y archivos mayores de 64 MiB; limita el lote a 100.000 objetivos. La comparación agrupa patrones de evidencia —como máximo 27 por conjunto de familias aplicables— en lugar de comparar todos los pares de contratos.

No se modifica la lógica de entrenamiento, el criterio de aprobación ni las métricas del modelo. La mejora actúa sobre la referencia descriptiva candidata; no añade dependencias a API, entrenamiento o inferencia.

## Resultado con datos reales guardados

Se reutilizaron las mismas entradas locales congeladas de la cohorte y sus 13 historias, sin consultas o escrituras en la base original. El [informe integrado revisión 3](EVALUACION_CONJUNTA_FAMILIAS_2017_REV3_20261020.json) conserva las detecciones anteriores y añade prioridades:

| Resultado | Cantidad |
| --- | ---: |
| Objetivos conservados | 1.698 |
| Historias admitidas | 13 |
| Operaciones con señales confirmadas para revisión | 50 |
| Operaciones sin señales confirmadas que necesitan completar evidencia | 1.648 |
| Conteos completos de familias | 0 |
| Posiciones de prioridad completamente resueltas | 0 |

La falta de competencia y otras historias mantiene intervalos amplios. Este resultado impide afirmar que los 50 casos precedan a todos los demás por riesgo total; permite identificarlos como revisiones con evidencia estadística concreta. No se publica un ranking ficticio de 1 a 1.698.

El [análisis independiente](PRIORIZACION_ROBUSTA_COHORTE_2017_20261020.json) sobre el informe anterior permite contrastar la incorporación sin cambiar los hallazgos. La validación y reproducción del código final quedan en [VALIDACION_MEJORA_MOTOR_V8_20261020.json](VALIDACION_MEJORA_MOTOR_V8_20261020.json).

### Validación final

Pasaron **1.080 pruebas del backend**, cero fallos, errores u omisiones. Incluyen 23 casos nuevos de prioridad: empates sin desempatar por ID, independencia de etapas/aplicabilidad, ausencia de datos, familia OR, coherencia de cobertura, rechazo de entradas alteradas, CLI sin paquetes externos, reproducción y protección de salidas existentes. Una prueba con semilla fija verifica 7.200 límites de posición usando pesos interiores de la caja y completaciones de datos desconocidos. La prueba de reproducibilidad conserva idénticos bytes tanto en el análisis independiente como en la composición integrada desde 12 archivos congelados. No se modificó la interfaz ni se repitieron sus pruebas.

## Reproducción

Desde `Backend`, usando una salida nueva:

```powershell
venv/Scripts/python.exe -I -S scripts/risk_robust_priority.py --input ../docs/analitica/EVALUACION_CONJUNTA_FAMILIAS_2017_REV2_20261019.json --output priorizacion-nueva.json
```

La composición integrada utiliza el manifiesto privado existente y verifica sus hashes antes de calcular. Los informes incluyen hashes del archivo de entrada y del código; el resultado no demuestra por sí mismo consistencia de generación de toda la base. La reproducción congelada usa biblioteca estándar y no consulta fuentes.

## Límites conservados

Los pesos históricos 1/1,5/2 y el corte publicado del 01/10/2026 permanecen intactos. La referencia 1/1/1 y el margen de sensibilidad no están calibrados. No hay modelos judiciales reales aprobados, índice ciudadano nuevo ni activación de sincronización diaria. La validación predictiva y de recursos a volumen completo seguirá siendo obligatoria antes de activar un candidato real. No se contacta a terceros.
