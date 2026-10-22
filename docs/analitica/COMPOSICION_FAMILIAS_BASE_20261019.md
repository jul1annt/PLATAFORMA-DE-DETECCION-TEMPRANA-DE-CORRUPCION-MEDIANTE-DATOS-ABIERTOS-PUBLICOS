# Composición de familias por operación y pesos base v5

## Resultado disponible

La [política v5](POLITICA_PESOS_BASE_V5.json) conserva los pesos históricos y los pesos de referencia. Añade una evaluación conjunta, reproducible y descriptiva de las familias por operación. No incorpora entrenamiento, una calibración predictiva o una publicación nueva.

| Familia | Peso de referencia | Regla de contribución |
|---|---:|---|
| Importe atípico | 1 | Cero o uno, cuando IQR sea evaluable |
| Competencia | 1 | Solo cuando su semántica y aplicabilidad estén verificadas |
| Concentración/reiteración | 1 | Máximo un punto aunque se detecten ambos indicadores móviles |

La igualdad es una referencia transparente ante la ausencia de evidencia para preferir una familia. **No es una estimación de importancia causal ni un resultado aprendido.** Los coeficientes históricos 1 / 1,5 / 2 se conservan como referencia legada; no se modificó la configuración operativa.

## Comprobaciones antes de combinar

El módulo puro `Backend/modules/motor_riesgo/joint_baseline.py` recalcula IQR a partir del grupo completo y procesa las historias una a la vez. No consume el puntaje final de proveedor ni los agregados legados como variables del contrato.

Cada historia debe apuntar a un objetivo seleccionado único de la cohorte. Se comprueban fuente, proceso, adjudicación, identidad no ambigua, estado de adjudicación, categoría, modalidad e importe del objetivo. La modalidad se compara tras normalizar acentos y espacios; los importes numéricos equivalentes no se consideran cambios por diferencias de formato. No se infieren equivalencias de códigos de categoría con versiones diferentes.

El corte declarado y el alcance descriptivo deben coincidir. La fecha del objetivo no puede ser posterior al cierre del día del corte en Bogotá ni anterior a su publicación. Una historia incompatible deja sin evaluar sus ventanas y conserva el IQR que pueda comprobarse. Una entrada duplicada o sin objetivo seleccionado hace fallar la composición completa, sin elegir arbitrariamente una historia.

Estas verificaciones **no prueban una generación común de base de datos**. La salida conserva `database_generation_consistency_verified=false`: coincidir en fecha de corte y hechos del objetivo no demuestra que todas las filas de referencia provengan de una misma transacción o generación. Las entradas quedan congeladas por hashes para esta evaluación exploratoria.

La referencia IQR utiliza todo el grupo del corte; las ventanas de este piloto se anclan en la adjudicación y se reconstruyen con datos del corte actual. Esa combinación permite una descripción del corte, no una predicción histórica sin futuro. Todas las salidas son inelegibles para entrenamiento y publicación del índice de modelos.

## Resultado de la cohorte local

Se evaluaron las **1.698 filas objetivo** de la cohorte de publicación de 2017 ya utilizada, sin nuevas consultas de base de datos. No todas tienen una identidad de operación comprobable. Las 13 historias de pares guardadas superaron los controles de hechos compartidos.

| Familia | Señal detectada | Sin señal observada | No evaluable |
|---|---:|---:|---:|
| Importe atípico | 50 | 1.342 | 306 |
| Competencia | 0 | 0 | 1.698 |
| Concentración/reiteración | 0 | 13 | 1.685 |

En las 13 operaciones con ventanas disponibles, cuatro tienen señal IQR y nueve no la tienen. Como competencia permanece desconocida, **ninguna de las 1.698 filas objetivo obtiene un conteo descriptivo completo**. No se asigna riesgo bajo a las demás ni se calcula un índice de 0 a 100.

En las nueve operaciones con IQR y ventanas sin señal, el intervalo de familias posibles es `[0,1]`; en las cuatro con IQR detectado y ventanas sin señal, `[1,2]`. Son límites derivados de la falta de evaluación de competencia, no intervalos de confianza ni probabilidades de corrupción.

El [informe principal, revisión 2](EVALUACION_CONJUNTA_FAMILIAS_2017_REV2_20261019.json) contiene cada operación, su cobertura, referencia IQR y hashes de historia. La primera ejecución se conserva como antecedente. La revisión redujo la memoria retenida: guarda resúmenes compactos, no todas las adjudicaciones de todas las historias, y produjo los mismos resultados.

## Ejecución, dependencias y reproducción

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_joint_baseline.py --manifest Backend/.codex-analytics-postgres/joint-baseline-cohort-2017-input-20261019.json --output evaluacion-conjunta-nueva.json
```

El manifiesto `joint-baseline-input-v1` identifica un archivo `cohort` y una lista `histories`, cada uno con `path` relativo y `sha256`. Se comprueban sus hashes y límites: 1 MiB de manifiesto, 16 MiB por archivo, 256 MiB acumulados y 1.000 historias. Se rechazan escapes de directorio, archivos repetidos y salidas existentes. Las historias se leen en serie y los datos originales siguen disponibles como evidencia congelada.

El comando utiliza biblioteca estándar. Se congelaron diez archivos de implementación e inicialización; una ejecución con Python `-I -S`, sin paquetes externos y desde otro directorio, reprodujo el informe byte por byte. El cálculo principal y esa reproducción tardaron aproximadamente 1,29 segundos en conjunto para estas entradas pequeñas; no es una medición del universo completo.

Pasaron **145 pruebas enfocadas**, incluidas **31 de composición**. Verifican incompatibilidades de identidad, etapa, corte y hechos; historia ausente; fecha inválida; monto faltante con ventanas utilizables; reiteración y directas limitadas a una familia; rechazo de duplicados; y reproducción con hashes. También comprueban que un importe extremo no supere el punto máximo de su familia ni que el riesgo de proveedor se traslade al contrato. Son pruebas enfocadas; la batería completa de 958 corresponde a la integración anterior del materializador, no a una nueva ejecución completa de esta composición.

El [recibo de validación](VALIDACION_COMPOSICION_FAMILIAS_20261019.json) enlaza pruebas, inputs, código congelado y salida. No se consultaron bases de datos, añadieron dependencias, entrenaron modelos o contactaron terceros en esta entrega.

## Estado de la base y pasos siguientes

| Componente | Estado |
|---|---|
| IQR por categoría, modalidad y periodo | Implementado; piloto con grupo completo y abstenciones |
| Ventanas móviles y calidad por operación | Referencia y captura SQL de diagnóstico integradas |
| Composición y límite de un punto por familia | Implementados; piloto reproducido |
| Evaluación de escalas y sensibilidad legada | Documentada sobre 31.731 resultados de proveedor; no prueba rendimiento predictivo |
| Pesos de referencia | Fijados en uno por familia, sin calibración predictiva |
| Semántica y cobertura de competencia | Pendientes |
| Denominador y cobertura anual de concentración | Pendientes de revisión separada |
| Más categorías, modalidades y periodos | Pendientes; el piloto no representa todo SECOP |
| Generación común y recursos a volumen completo | Pendientes antes de integración operativa/publicación |
| Modelos entrenados con positivos judiciales firmes | Pendientes de evidencia y validación del plan |

El siguiente desarrollo debe resolver competencia y cobertura anual sin repetir los componentes ya implementados. La política v5 no habilita automáticamente un índice ni cambia el corte ciudadano conservado del 01/10/2026.
