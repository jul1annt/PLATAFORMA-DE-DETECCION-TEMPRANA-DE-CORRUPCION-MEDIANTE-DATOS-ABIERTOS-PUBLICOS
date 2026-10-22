# Desarrollo de la base: cobertura por operación

## Cambio implementado

Se completó el primer paso técnico de la base acordada: distinguir información no evaluable, señales ausentes e indicadores que no corresponden a la etapa. La política vigente para este desarrollo es [pesos base v2](POLITICA_PESOS_BASE_V2.json). La v1 permanece como antecedente; los pesos de la plataforma publicada no cambiaron.

`Backend/modules/motor_riesgo/baseline_coverage.py` es un módulo de dominio con biblioteca estándar, independiente de persistencia, API y bibliotecas de entrenamiento. El comparador cronológico de `rules.py` lo utiliza y conserva cuatro estados:

| Estado | Significado | Contribución |
| --- | --- | --- |
| `DETECTADA` | Se cumple la regla con datos evaluables | 1 por familia |
| `SIN_SENAL` | Hay datos suficientes y no se cumple la regla | 0 |
| `NO_EVALUABLE` | Falta un requisito o hay un dato inválido | Desconocida |
| `NO_APLICA` | El indicador no corresponde a la etapa o modalidad | Fuera del denominador |

Convocatoria solo aplica la familia IQR implementada actualmente; no utiliza adjudicatario, oferentes ni reiteraciones futuras. Adjudicación agrega competencia y concentración/reiteración. Esto describe las familias de esta referencia: no es un catálogo exhaustivo de todos los riesgos posibles en convocatoria.

## Puntaje y cobertura

- `confirmed_signal_count`: número mínimo de familias con señal demostrada. No constituye un riesgo completo cuando faltan familias aplicables.
- `complete_score`: solo tiene valor cuando todas las familias aplicables tienen resultado determinado. En caso contrario es `null`.
- `score_interval`: mínimo confirmado y máximo posible al resolver las familias desconocidas. Es incertidumbre por datos faltantes, **no** un intervalo de confianza, porcentaje ni probabilidad de corrupción.
- Cobertura por familia y por indicador, valores observados, umbrales y motivos de no evaluación.

Por ejemplo, si se detecta concentración, IQR no es evaluable y competencia no aplica por modalidad directa, el intervalo es `[1,2]`, el puntaje completo es `null` y la señal de concentración se conserva. Si directas supera su umbral y reiteración es desconocida, la familia OR ya es positiva; se conserva que uno de sus indicadores sigue sin evaluación. Dos indicadores positivos de esa familia no cuentan dos veces.

No se redistribuyen pesos entre las familias disponibles. Así, un registro con una única familia evaluable no recibe automáticamente un índice máximo ni se compara como si tuviera cobertura completa.

## Requisitos que ahora se hacen explícitos

- Oferente único: no se evalúa automáticamente mientras su semántica no esté verificada. Las modalidades se reconocen mediante un diccionario explícito; no se asume competencia por contener una subcadena. El evaluador puro admite verificación semántica explícita para desarrollo, pero el comparador cronológico mantiene esa señal deshabilitada.
- Los conteos deben ser finitos, enteros y no negativos. Cero oferentes en una adjudicación no acredita competencia normal.
- IQR: importes positivos y finitos, grupo suficiente y dispersión positiva. Los pares inválidos no aumentan el mínimo de 30; se informa cuántos fueron descartados.
- Fechas: los instantes con zonas horarias distintas se agrupan y ordenan por tiempo UTC. No entran pares posteriores al instante objetivo. Los grupos anuales usan el año UTC del instante, consistente con las observaciones normalizadas del motor.
- Categoría o modalidad ausentes: no se arma un grupo IQR aparentemente válido con otros valores ausentes.
- No se permite mezclar filas con etapas declaradas distintas en un mismo comparador.

## Entrenamiento y aprobación futuros

La salida numérica del comparador conserva el conteo mínimo para los análisis internos y lleva la marca `confirmed_signal_count_lower_bound`. Los informes contienen conteos agregados de estados y hash del detalle por operación; no incorporan toda esa matriz dentro del informe del modelo. El CLI de diagnóstico sí permite conservar el detalle completo.

Un entrenamiento no se declara validado si su comparador tiene filas incompletas, aunque el intervalo estadístico de mejora resulte favorable. La política común de aprobación también rechaza informes sin cobertura acreditada, política vigente o hash válido del detalle. Los informes antiguos sin esta evidencia necesitan una evaluación nueva antes de una aprobación futura. No se borran publicaciones históricas ni se reejecuta su inferencia.

El manifiesto de entrenamiento incorpora el hash del módulo nuevo. Inferencia no importa entrenamiento ni añade dependencias. Como la semántica de oferentes sigue pendiente, las comparaciones de adjudicación en modalidades competitivas no pueden aprobarse usando cobertura desconocida como cero.

## Diagnóstico desconectado

`Backend/scripts/risk_baseline_coverage.py` recibe un JSON con `stage`, `history` y `targets`. Cada fila contiene `prediction_at` y las variables preparadas en `values`; opcionalmente las identidades y etapa ya utilizadas por el comparador. Los importes se suministran como `log_presupuesto` o `log_adjudicado`, calculados mediante logaritmo natural de uno más el importe nominal COP.

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_baseline_coverage.py --input observaciones-preparadas.json --output cobertura-nueva.json
```

El comando limita la entrada a 16 MiB y 10.000 observaciones en conjunto, conserva el orden de objetivos, enlaza datos y código por hash y no sobrescribe un resultado existente. No conecta a bases, descarga documentos, entrena o publica. Las variables de entrada deben tener procedencia revisada: el diagnóstico por sí mismo no acredita identidades o reconstrucción histórica.

## Estado del plan de desarrollo

La [validación conservada](VALIDACION_COBERTURA_BASE_20261019.json) registra 788 pruebas del backend correctas y una ejecución posterior de las 38 pruebas enfocadas en cobertura, incluida la nueva prueba del CLI. Son conjuntos superpuestos, no 826 pruebas distintas. El primer ensayo enfocado tuvo 84 éxitos y un fallo: un fixture de entrenamiento usaba un IQR constante. Se corrigió el fixture para aportar presupuestos comparables con dispersión sin convertir presupuesto en etiqueta. La repetición de 142 pruebas enfocadas y las ejecuciones finales pasaron sin errores u omisiones.

Las lecturas posteriores comprobaron esquema y cero modelos/evidencias en la base aislada, publicación analítica desactivada y pesos legados intactos en la base operativa. El manifiesto publicado conserva su referencia y corte. No se instaló la revisión candidata sobre el paquete publicado.

1. **Implementado:** cobertura por operación, familias y etapas, motivos, intervalos de datos desconocidos y control de aprobación.
2. **Avance posterior:** [comparación de cinco transformaciones y referencia congelada](NORMALIZACION_Y_ESTABILIDAD_BASE_20261019.md) sobre el censo de resultados legados de una ejecución. Falta la evaluación equivalente de familias corregidas por operación.
3. **Avance posterior:** estabilidad y redundancia globales del marco legado evaluadas; sigue pendiente segmentación por sector, periodo y modalidad con unidades contractuales válidas.
4. **Pendiente para modelos futuros:** corpus judicial suficiente y evaluación independiente por etapa.
5. **Pendiente para activación:** aprobación metodológica y operativa completa.

La referencia no está publicada como índice ciudadano. Los pesos legados, la base operativa y el corte del 01/10/2026 se conservan. No se contactó a terceros ni se reanudó la adquisición judicial.
