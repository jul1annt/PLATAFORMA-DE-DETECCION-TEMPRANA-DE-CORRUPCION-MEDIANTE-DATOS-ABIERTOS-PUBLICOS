# Contexto anual: denominador, cobertura y exclusión del objetivo

## Qué se corrigió

El cálculo anual de diagnóstico podía omitir adjudicaciones sin fecha cuando decidía si el denominador estaba completo. También incluía el proceso que se estaba evaluando. La política `buyer-annual-process-participation-v1` corrige ambos comportamientos y separa los datos necesarios para cada variable.

- La fecha de publicación sirve para contar procesos publicados previamente.
- La fecha de adjudicación sirve para el contexto de proveedores adjudicatarios.
- Una fecha desconocida que pueda afectar una ventana se conserva como incertidumbre; no se sustituye ni se elimina para completar el denominador.
- El proceso objetivo se excluye por fuente y proceso, con todas sus adjudicaciones y fallos de calidad.
- Las filas sin normalizar pero con una clave raw de entidad conocida no desaparecen del control de cobertura. Las claves raw y normalizadas incompatibles afectan a ambos grupos conocidos, sin elegir una entidad por nombre.
- La ausencia de fecha de publicación no elimina una adjudicación cuya fecha sea comprobable. La falta de proveedor impide certificar la participación anual, pero no descarta automáticamente todas las demás señales.

Estos cambios están en la captura de diagnóstico del código local. La captura diaria normal sigue utilizando evidencia revisada de etapa; no se sustituyó por una reconstrucción retrospectiva de los contratos guardados.

## Definición de la medida

La ventana es `[t − 8.760 horas, t]`, con extremos inclusivos e instantes normalizados a UTC. No es el año calendario.

Para una entidad según sus claves almacenadas y las fuentes seleccionadas:

1. `N` cuenta procesos distintos con adjudicación dentro de la ventana, excluido el objetivo.
2. `n_s` cuenta procesos distintos en los que figura el proveedor `s` como adjudicatario.
3. La medida es `max(n_s) / N`, únicamente cuando `N > 0` y no hay incertidumbre que afecte el marco.

Es la **participación máxima de un proveedor en procesos de la entidad**. No es una cuota monetaria, un índice HHI ni una medida validada del mercado económico. Varias adjudicaciones del mismo proveedor en un proceso cuentan una vez. Un proceso con varios adjudicatarios puede aportar presencia a varios proveedores; sus participaciones no tienen por qué sumar uno. Esta definición se conserva explícita en la metadata.

Un marco vacío no genera una concentración igual a cero. Un marco incompleto tampoco genera una razón sobre el subconjunto conocido. Los conteos observados se conservan como contexto, junto con los motivos de falta de completitud. El universo sigue siendo local y de claves conocidas, no toda la contratación de la entidad o del país.

## Procesamiento y separación

| Componente | Función |
|---|---|
| `annual_context.py` | Referencia pura, control de cobertura y regla de recorte temporal |
| `annual_materialize.py` | Agregados SQL por entidad, proceso y proveedor; conserva calidad |
| `history.py` | Orquesta captura y contextos de 30/90 días y anual |
| `feature_store.py` | Excluye el objetivo usando agregados indexados y devuelve cobertura |
| `feature_builder.py` | Solo admite valores con la política anual y una identidad objetivo válida |
| `risk_annual_context.py` | Ejecuta el diagnóstico sobre un archivo congelado, sin consultar la base |

No se busca la historia completa por cada contrato. Los agregados se preparan una vez. Para excluir el objetivo del máximo se comprueba si todos los proveedores empatados en el máximo participaron en su proceso: en ese caso se reduce el máximo en uno; si alguno no participó, el máximo permanece. La referencia Python calcula directamente sobre los demás procesos para contrastar esa optimización.

El recorte temporal ocurre antes de proyectar y normalizar toda la historia anual. Conserva fechas desconocidas que puedan influir y elimina únicamente filas que no afectan ninguna de las dos ventanas. Se comparó contra la evaluación sin recorte en 100 marcos mixtos reproducibles, además de los casos de límites, identidad y normalización.

El manifiesto de entrenamiento incluye ahora hashes de `annual_context.py`, `annual_materialize.py`, `rolling_materialize.py` y `method_reference.py`, además de los constructores que ya registraba. Leer esos hashes no importa SQLAlchemy en el entorno de entrenamiento; el ensayo de separación de dependencias lo comprueba. No se añadieron paquetes a API, entrenamiento o inferencia.

## Validación con datos guardados

Se eligió el objetivo local 347175 del piloto anterior y se leyó el marco temporalmente relevante de su **clave exacta de entidad almacenada**, en una transacción repetible de solo lectura de la base original OID 24577. La consulta terminó con **1.478 filas**, por debajo del límite de 20.000. Se conservaron el snapshot de PostgreSQL, la consulta, hashes y controles de identidad. No se infirieron equivalencias con otras representaciones de la entidad fuera de esa clave.

El ancla es la adjudicación registrada del objetivo de 2017, pero los registros se observaron en 2026. Esto es una descripción retrospectiva del archivo actual, no evidencia de disponibilidad histórica para entrenar.

| Resultado del marco real | Valor |
|---|---:|
| Filas adquiridas | 1.478 |
| Procesos con publicación observada en la ventana | 1.190 |
| Filas que impiden certificar ese conteo | 231 |
| Procesos con fecha de adjudicación observada en la ventana | 872 |
| Filas que impiden certificar el contexto adjudicado | 854 |
| Máximo de procesos observado para una clave de proveedor admisible | 7 |
| Frecuencia previa completa | No evaluable |
| Participación anual completa | No evaluable |

Los 231 y 854 son **filas con problemas para cada cálculo**, no cantidades de procesos corruptos ni grupos disjuntos. Los 1.190 y 872 son observaciones del marco, no denominadores completos acreditados. Por ello no se calculó `7/872` ni una razón sobre los proveedores conocidos únicamente.

La misma proyección y sus controles de identidad archivados se ejecutaron a través del materializador, lector y constructor reales en la base aislada OID 82244. Solo se crearon e insertaron tablas temporales; no se escribieron tablas permanentes. Los conteos y controles coincidieron con la referencia y ambas variables numéricas quedaron ausentes de las variables del objetivo. Se revirtió la transacción y se comprobó que las tablas temporales desaparecieron. No es una réplica completa de raw ni una nueva comprobación de todos los alias de la fuente.

El [diagnóstico real](AUDITORIA_CONTEXTO_ANUAL_20261020.json), la [comparación SQL](COMPARACION_ANUAL_SQL_PILOTO_20261020.json) y el [recibo de validación](VALIDACION_CONTEXTO_ANUAL_20261020.json) documentan el alcance y sus hashes.

## Extracción y tiempos

La primera consulta alcanzó diez segundos sin devolver filas. Una variante que seleccionó IDs por entidad y enlazó la normalización mediante búsquedas acotadas comenzó a devolver datos, pero se detuvo después de 13.500 filas para evitar recorrer años irrelevantes. Ninguna lectura incompleta se utilizó como marco válido.

La extracción final añadió el filtro temporal equivalente, conservando fechas desconocidas, y terminó con las 1.478 filas en aproximadamente 116 segundos. No se amplió el límite de diez segundos por consulta/fetch ni se modificaron índices de producción. Los planes y los intentos se conservaron. Estos ensayos no son una comparación de rendimiento controlada ni acreditan tiempos para el universo completo.

El diagnóstico desconectado y su reproducción desde cinco archivos de código congelados tardaron en conjunto alrededor de 0,43 segundos. No volvieron a leer la base. La reproducción con Python `-I -S`, sin paquetes externos, produjo el mismo archivo byte por byte. Se comprobó el rechazo de sobrescritura y el comportamiento de marcos completos y parciales.

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_annual_context.py --input Backend/.codex-analytics-postgres/annual-buyer-input-20261020.json --output contexto-anual-nuevo.json
```

## Pruebas y efecto en los pesos

Pasaron las **1.053 pruebas del backend**, sin fallos o saltos, después de los cambios del cálculo y el manifiesto. Incluyen **36 casos nuevos** de referencia e integración anual, uno de los cuales compara 100 marcos mixtos. Cubren múltiples adjudicaciones y adjudicatarios, empates de proveedores, identificadores compartidos entre fuentes, normalización ausente o incompatible, raw aún no procesado, fechas desconocidas, alias, límites exactos y cambios de zona horaria de la sesión. El CLI desconectado se comprobó además con el marco real, una reproducción congelada y dos casos de completitud.

La [política v7](POLITICA_PESOS_BASE_V7.json) conserva los coeficientes históricos y el punto de referencia por familia. No añade un umbral de riesgo anual ni convierte este contexto en un punto adicional. No se entrenaron modelos reales, activó una publicación, alteró el corte ciudadano o contactó a terceros.

La corrección anual y su control de cobertura quedan implementados. Sigue sin existir evidencia suficiente para valorar todas las señales del corte o calibrar pesos predictivos. El siguiente paso es la auditoría final del conjunto de la base y sus entregables, distinguiendo la referencia de desarrollo de la fase futura de entrenamiento y activación condicionada.
