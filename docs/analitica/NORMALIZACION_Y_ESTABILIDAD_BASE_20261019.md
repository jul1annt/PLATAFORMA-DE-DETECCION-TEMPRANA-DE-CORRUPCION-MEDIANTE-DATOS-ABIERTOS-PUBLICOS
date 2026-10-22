# Normalización y estabilidad de la base analítica

## Alcance completado

Se implementó un laboratorio desconectado para comparar escalas, pesos, prioridades y redundancia de componentes. Se ejecutó sobre el **censo de 31.731 resultados de proveedor** de la ejecución legada `154b21cd-89dd-47b1-a45e-ec48dd8d9f86`, registrada como exitosa. La extracción en una transacción consistente de solo lectura coincidió con los 31.731 resultados declarados por la ejecución y conservó claves únicas de resultado.

Esto sustituye el muestreo por clave primaria para esta comparación: se examinan todos los resultados de esa ejecución. **El marco no es todo SECOP ni todos los proveedores**, sino quienes tienen resultado guardado en esa ejecución del motor. No es un censo de corrupción y no permite estimar capacidad predictiva. Se trata de riesgo agregado por proveedor, no de las familias corregidas por operación y etapa.

No se extrajeron nombres ni NIT. La entrada y la referencia quedan en el directorio privado de análisis; los informes contienen agregados, metadatos del alcance y hashes. No hubo escrituras en la base, reingesta o modificación del corte publicado.

## Alternativas comparadas

| Alternativa | Tratamiento de componentes | Pesos |
| --- | --- | --- |
| Legado | Escalas originales | 1 / 1,5 / 2 |
| Escalas originales con pesos iguales | Escalas originales | 1 / 1 / 1 |
| Acotado con pesos legados | IQR: `s/(1+s)`; reiteración y directa: `s/10` | 1 / 1,5 / 2 |
| Acotado con pesos iguales | Las mismas transformaciones acotadas | 1 / 1 / 1 |
| ECDF con pesos iguales | Posición respecto de una referencia empírica congelada | 1 / 1 / 1 |

Las transformaciones acotadas llevan cada componente al intervalo de 0 a 1. El agregado es una suma de contribuciones, **no** una probabilidad ni un índice ciudadano de 0 a 100. El parámetro de suavización del IQR es una unidad de exceso IQR, una referencia operativa que no fue optimizada contra etiquetas.

La ECDF preserva los ceros como ceros numéricos y utiliza rangos medios en empates de valores positivos. Preservar un cero histórico no acredita que el indicador tuviera cobertura. La referencia contiene la distribución de cada componente, cantidad, alcance y hash. Se puede aplicar a valores nuevos sin recalcular sus cuantiles. Es una referencia descriptiva de este corte: **no estaba disponible retrospectivamente en convocatoria** y no se admite como variable histórica por el solo hecho de quedar congelada ahora.

## Resultados del censo

| Alternativa | Participación IQR en la suma | Coincidencia con el legado en el 5 % prioritario |
| --- | ---: | ---: |
| Legado | 99,9988 % | 100 % |
| Escalas originales, pesos iguales | 99,9992 % | 95,65 % |
| Acotado, pesos legados | 28,39 % | 72,08 % |
| Acotado, pesos iguales | 37,32 % | 72,20 % |
| ECDF, pesos iguales | 46,91 % | 70,31 % |

**Igualar pesos sin tratar escalas no elimina la dominancia del IQR.** Las transformaciones cambian una parte importante de las prioridades. La coincidencia compara masa de selección, no un número entero de proveedores, porque el 5 % de 31.731 no es entero y puede cortar un grupo empatado.

La correlación de rangos entre el acotado de pesos iguales y el legado es 0,9873, aunque la coincidencia en su 5 % prioritario es solo 72,20 %. Una correlación global alta no garantiza que se revisen los mismos primeros casos.

Con transformaciones acotadas y pesos iguales, reiteración aporta 62,48 % y directa 0,21 % de la suma. Estos porcentajes describen valores y frecuencias observados en componentes legados; no estiman importancia causal ni gravedad. Tampoco se asignan automáticamente a indicadores nuevos que tienen otras fórmulas y unidades.

### Sensibilidad local de pesos

Al variar un solo peso ±20 % respecto de pesos iguales, se conserva al menos:

- **98,86 %** de la masa del 5 % prioritario en la variante acotada.
- **98,80 %** en la variante ECDF.

Esta estabilidad es local a esos cambios, ese marco y esas fórmulas. No demuestra que ninguna variante sea correcta o mejor para detectar corrupción. No se ajustaron pesos buscando máxima coincidencia con el legado.

### Redundancia de componentes

Correlaciones de Spearman en el marco completo:

| Componentes legados | Correlación |
| --- | ---: |
| IQR y reiteración | 0,2517 |
| IQR y directa | 0,0123 |
| Reiteración y directa | 0,0478 |

No se interpreta una correlación baja como independencia causal ni se eliminan indicadores por estas cifras. Las escalas y los numerosos empates exigen conservar el análisis de selección prioritaria. Un componente constante produce correlación indefinida, no cero.

## Implementación y reproducción

- `Backend/modules/motor_riesgo/weight_lab.py`: validación del marco, transformaciones, referencia congelada, comparación de rankings con empates, correlaciones y sensibilidad.
- `Backend/scripts/risk_normalization_lab.py`: comando independiente que lee una entrada explícita y genera dos archivos nuevos. No importa API, persistencia o bibliotecas de aprendizaje.
- `Backend/tests/test_weight_lab.py`: cobertura de empates, referencias alteradas, datos ausentes/no finitos, duplicados, límites de escala, entradas vacías, estabilidad respecto de precisión decimal ambiental y conservación de archivos.

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_normalization_lab.py --input Backend/.codex-analytics-postgres/normalization-census-input-20261019.json --output comparacion-nueva.json --reference referencia-nueva.json
```

El comando rechaza salidas existentes o coincidentes, entradas mayores de 64 MiB, más de 100.000 resultados, claves duplicadas y cantidades incompatibles con el marco declarado. Los componentes legados que excedan sus límites documentados requieren revisión; no se recortan silenciosamente. No convierte ausencias en ceros. La precisión decimal se fija en 28 posiciones durante el cálculo, con independencia del contexto ambiental.

La comparación utiliza inclusión fraccionaria en empates, sin desempatar por nombre o identificador. Una referencia alterada, incompleta, desordenada o con política desconocida se rechaza. Los hashes distinguen el contenido de la referencia, el archivo de entrada y el código exacto usado.

## Evidencia y límites de validación

La [revisión vigente del resultado](COMPARACION_NORMALIZACIONES_REV3_20261019.json) enlaza su referencia congelada. La [validación](VALIDACION_NORMALIZACIONES_20261019.json) conserva hashes, alcance, ejecución y **63 pruebas enfocadas correctas**, que incluyen las 38 pruebas de cobertura ya existentes; no son 63 pruebas adicionales. Se repitió la evaluación desconectada completa y coincidió exactamente con el resultado conservado y su referencia.

Las revisiones 1 y 2 se conservan como antecedentes: se reforzaron validaciones de identidad/cantidad, manejo de empates y contexto decimal antes de la revisión 3. No cambiaron los datos de entrada ni el alcance. No se volvió a ejecutar la batería general del backend para estos módulos nuevos de laboratorio desconectado; la ejecución enfocada y el censo completo son la evidencia de este cambio.

Este trabajo prueba aritmética, reproducibilidad y estabilidad descriptiva del marco. No entrena modelos, verifica sentencias, mide precisión judicial o valida variables históricas. La política vigente de desarrollo es [pesos base v3](POLITICA_PESOS_BASE_V3.json). Los pesos productivos siguen siendo 1 / 1,5 / 2; no se seleccionó ni activó otra alternativa.

## Estado de los pasos siguientes

1. Cobertura por operación: implementada en la referencia por etapas.
2. Transformaciones y referencia congelada: implementadas y evaluadas sobre un marco completo de resultados legados. Falta repetir la comparación sobre familias corregidas con cobertura documentada por operación; el resultado agregado por proveedor no sustituye esa evaluación.
3. Estabilidad y redundancia globales: evaluadas en ese marco. La [estratificación contractual posterior](ESTRATIFICACION_BASE_METODOLOGIA_20261019.md) implementa segmentación y cobertura con identidades explícitas; se abstiene de comparaciones conjuntas porque solo hay 24 unidades con ambos componentes observados en la selección. No se atribuye a cada contrato un puntaje agregado de proveedor para fabricar esos segmentos.
4. Modelos judiciales: pendientes de corpus suficiente y validación independiente.
5. Publicación nueva: permanece pendiente de los requisitos metodológicos y operativos.
