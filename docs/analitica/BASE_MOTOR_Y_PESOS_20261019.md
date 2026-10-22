# Base del motor analítico y de los pesos de riesgo

Estado posterior: la [política v7](POLITICA_PESOS_BASE_V7.json) añade la [corrección y cobertura del contexto anual](CONTEXTO_ANUAL_BASE_20261020.md), junto con la auditoría semántica de competencia, composición por operación, cobertura, normalización, estratificación y ventanas SQL. Los valores sin cobertura suficiente permanecen ausentes. La configuración histórica y la evaluación inicial de pesos descritas aquí se conservan. Los datos descriptivos del corte no se admiten automáticamente para entrenar modelos históricos.

Actualización del desarrollo: la [cobertura por operación](COBERTURA_BASE_ANALITICA_20261019.md) y la [política v2](POLITICA_PESOS_BASE_V2.json) completan el primer paso descrito al final. La evaluación de 2.000 resultados y las decisiones sobre el legado de este documento se conservan; sus observaciones sobre cobertura faltante describen el estado inicial v1 y quedan sustituidas por esa implementación.

## Entregable acordado

El usuario precisó el 19/10/2026 que necesita una base sólida para desarrollar después. Este entregable deja arquitectura, indicadores, parámetros, límites y una evaluación reproducible de los pesos actuales. El entrenamiento judicial y la activación de los dos modelos siguen siendo una evolución posterior sujeta a los criterios del plan; no son necesarios para describir y evaluar esta base. Solo se usa información pública y datos SECOP locales. No contactar a terceros.

## Resultado de la evaluación

Se consultaron en modo solo lectura los pesos y 2.000 resultados existentes de `riesgo_proveedor`, seleccionados por `ORDER BY id LIMIT 2000`, en una transacción consistente de la base local OID 24577. La muestra no es aleatoria ni representativa y puede contener ejecuciones históricas distintas. No se consultaron nombres o NIT ni se recalcularon contratos. El archivo de entrada queda en el directorio privado de evaluación; el informe público local contiene solo agregados y hashes.

Los 2.000 resultados coinciden con la fórmula y los pesos guardados en cada ejecución, con tolerancia de 0,011 para la puntuación histórica calculada mediante float y redondeada a dos decimales. No se encontraron pesos aplicados diferentes a los actuales en esta muestra. Esto comprueba coherencia aritmética, no calidad de detección.

| Componente legado | Escala de la fórmula | Peso vigente | Máximo observado en la muestra |
| --- | --- | ---: | ---: |
| IQR / `OUTLIER` | Distancia fuera del límite dividida por IQR; sin máximo | 1,00 | 10.705.640.607,6512 |
| Reiteración / `DUPLICADO_CORTO` | `10 - días*(10/30)` para pares detectados en 30 días | 1,50 | 10 |
| Directa / `ABUSO_DIRECTO` | Porcentaje de contratación directa dividido entre 10 | 2,00 | 10 |

El IQR aporta el **99,9999097 % de la suma ponderada** de esta muestra. No significa que aporte ese porcentaje a cada resultado ni al universo. El hallazgo evidencia que las unidades dominan el agregado: un IQR positivo pero diminuto puede generar una puntuación enorme. Aumentar o reducir pesos sin tratar las escalas no produce un índice comparable ni calibra corrupción.

### Sensibilidad de las clasificaciones actuales

Se mantuvieron los umbrales históricos de 2 y 5 y se varió un solo peso cada vez. La comparación usa la puntuación sin redondear, como la clasificación implementada.

| Peso modificado | Reducir 20 %: resultados que cambian de clase | Aumentar 20 %: resultados que cambian de clase |
| --- | ---: | ---: |
| IQR | 34 / 2.000 (1,70 %) | 28 / 2.000 (1,40 %) |
| Reiteración | 7 / 2.000 (0,35 %) | 10 / 2.000 (0,50 %) |
| Directa | 0 / 2.000 | 0 / 2.000 |

La estabilidad de una clase no acredita su validez. La dominancia en suma y los cambios de clase son medidas diferentes. No se calcularon precisión, falsos positivos, detección judicial, prevalencia ni pesos óptimos. Los ceros legados tampoco demuestran que hubiera datos suficientes para evaluar cada señal.

Informe: [evaluación reproducible](EVALUACION_PESOS_BASE_20261019.json).

## Decisión sobre los pesos

### Legado publicado: conservar para trazabilidad

Se conservan **1 / 1,5 / 2** con sus umbrales históricos, identificados como configuración manual no calibrada. Cambiarlos alteraría la interpretación de resultados existentes sin demostrar una mejora. No se equiparan a porcentajes de importancia y no se reutilizarán directamente como coeficientes de los futuros modelos.

### Referencia de desarrollo: familias comparables

La referencia independiente ya implementada en `rules.py:chronological_baseline` utiliza detecciones binarias y un peso de **1 por familia**:

1. Importe atípico: una contribución si el IQR de pares comparables detecta anomalía.
2. Competencia: una contribución por oferente único en modalidad competitiva, únicamente con campo semánticamente verificado. Su captura automática continúa deshabilitada.
3. Concentración/reiteración: una contribución si se cumple la regla de directas en 90 días o reiteraciones en 30 días. Ambas simultáneas siguen aportando como máximo una unidad de esa familia.

La igualdad de pesos es una referencia de ingeniería transparente ante la falta de evidencia para privilegiar una familia. No implica igual capacidad predictiva demostrada. El conteo implementado puede llegar a 3; ese máximo no convierte el resultado en porcentaje ni habilita comparaciones entre etapas. Convocatoria y adjudicación tienen información y aplicabilidad diferentes.

Este comparador sigue siendo interno. Su salida actual incluye cobertura agregada del IQR, pero aún no una matriz completa de aplicabilidad y cobertura por familia y operación. Antes de presentar un agregado de esta referencia deberá añadirse esa matriz, conservar valores y motivos de no evaluación y evitar presentar un conteo parcial como un total completo. No se crean umbrales bajo/medio/alto ni un índice ciudadano nuevo con esta decisión.

La [política versionada](POLITICA_PESOS_BASE_V1.json) fija el estado y las condiciones de evolución. No se modificaron los pesos de la base de datos ni la publicación.

## Fundamento y límites de los indicadores

La [guía de Open Contracting](https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/) sustenta documentar indicadores, fórmulas y datos necesarios por etapa. La [adaptación colombiana de Fedesarrollo/IMCO](https://imco.org.mx/wp-content/uploads/2019/07/FEDESARROLLO_CPBD.pdf) aporta contexto sobre competencia, transparencia y anomalías y las restricciones de SECOP. Ninguna de estas referencias demuestra que los coeficientes locales 1 / 1,5 / 2, o nuestros umbrales y ventanas, sean óptimos.

El catálogo `modules/motor_riesgo/catalog.py` conserva fórmula, etapa, requisitos, fuente y limitación por indicador. IQR por categoría, modalidad y año exige al menos 30 observaciones independientes y dispersión positiva. Un importe total atípico no demuestra sobreprecio. Reiteración no demuestra duplicación o fraccionamiento y contratación directa no acredita ilegalidad. Las ventanas de 30/90 días, los mínimos de conteo y el multiplicador IQR son parámetros operativos sujetos a sensibilidad posterior.

## Separación para desarrollar después

| Responsabilidad | Implementación existente | Regla de dependencia |
| --- | --- | --- |
| Identidades, etapas y contratos de variables | `modules/motor_riesgo/domain.py` | Dominio sin dependencias de entrenamiento |
| Definición y cálculo de señales | `catalog.py`, `rules.py` | Reglas independientes de etiquetas judiciales |
| Construcción y evidencia de variables | `feature_builder.py`, `stage_evidence.py`, `feature_store.py` | Fechas y fuentes verificables; no información futura |
| Entrenamiento y evaluación | `analytics_ml/` | Proceso y entorno independientes de API e inferencia |
| Inferencia | `analytics_ml/inference.py`, `analytics_ml/runtime.py` | Proceso y entorno separados, lock de inferencia propio y artefactos aprobados; compartir directorio no implica importar bibliotecas de entrenamiento |
| Resultados y publicación | `result_store.py`, `publication.py` | Consulta sobre resultados persistidos y activación controlada |
| Evaluación de pesos legados | `scripts/risk_weight_assessment.py` | CLI con biblioteca estándar; sin DB, red, entrenamiento o publicación |

La entrada del nuevo CLI se obtiene mediante una extracción explícita y de solo lectura. El análisis posterior es desconectado. Añadir este CLI no cambia dependencias de API ni las del modelo. Los módulos citados son rutas relativas al directorio `Backend`.

## Cómo reproducir la evaluación

Desde la raíz del proyecto y conservando las revisiones anteriores:

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_weight_assessment.py --input Backend/.codex-analytics-postgres/weight-assessment-input-20261019.json --output evaluacion-pesos-nueva.json
```

El archivo privado de entrada no contiene nombres, NIT ni credenciales; conserva puntuaciones y pesos aplicados. El CLI verifica valores finitos no negativos, calcula contribuciones y sensibilidad, comprueba coherencia histórica y enlaza entrada y código por SHA-256. Se ejecutó sobre los 2.000 registros reales descritos. No se repitió la batería general del backend: no cambió el motor de ejecución ni su API.

## Próxima evolución técnica

1. **Implementado en la revisión v2:** cobertura por familia/operación e inaplicabilidad, dato ausente y ausencia de señal. Ver implementación y validación enlazadas al inicio.
2. Comparar conteo binario, transformaciones acotadas y referencias por población congelada con datos representativos; evitar ajustar a esta muestra por clave primaria.
3. Medir estabilidad de prioridades, redundancia y sensibilidad por sector, periodo y modalidad, preservando la cobertura.
4. Cuando haya corpus suficiente, comparar ambos modelos con las reglas y el azar usando separación temporal, expedientes relacionados y proveedores no vistos.
5. Activar únicamente después de la evaluación independiente y los controles operativos del plan original.

**Estado:** base metodológica y herramienta descriptiva disponibles; calibración judicial, modelos entrenados e índice ciudadano nuevo pendientes. La plataforma histórica del 01/10/2026 se conserva.
