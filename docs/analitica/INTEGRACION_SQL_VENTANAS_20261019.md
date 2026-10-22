# Ventanas estrictas integradas en la captura de diagnóstico

## Estado

La captura de diagnóstico con `include_current_context=True` utiliza ahora el materializador de conteos estrictos. Dejó de utilizar la coincidencia parcial de texto para identificar modalidades directas y conserva la abstención cuando faltan fechas, identidades o modalidad verificable. Este cambio está en el código local de desarrollo; no se activó un despliegue ni una publicación ciudadana.

La batería completa del backend terminó con **958 pruebas correctas, cero fallos y cero saltos**, en aproximadamente 99 segundos. Entre ellas hay 17 comprobaciones nuevas de la integración. El [recibo de validación](VALIDACION_INTEGRACION_SQL_VENTANAS_20261019.json) conserva el identificador de ejecución, hashes, versiones del entorno y copia local de los archivos cambiados.

## Separación de responsabilidades

| Componente | Responsabilidad |
|---|---|
| `method_reference.py` | Diccionario descriptivo explícito de modalidades; devuelve desconocido para etiquetas no reconocidas |
| `materialize.py` | Captura ordenada y detección de alias de la unidad fuente/proceso/adjudicación |
| `rolling_materialize.py` | Agregados SQL por par, categoría y proceso, con fallos de calidad conservados |
| `history.py` | Orquestación de contexto temporal; invoca el materializador estricto para 30/90 días |
| `feature_store.py` | Lectura de 1.000 filas por lote y exclusión del proceso objetivo mediante agregados indexados |
| `feature_builder.py` | Conversión a variables, guardas de identidad y procedencia; no accede a la base |
| `rolling_evidence.py` | Referencia desconectada para las comparaciones |

No se añadieron dependencias. SQLAlchemy permanece en persistencia y extracción. El diccionario y el constructor de variables utilizan biblioteca estándar y el dominio puro. Los entornos de entrenamiento e inferencia siguen separados.

## Reglas trasladadas

- Los conteos utilizan procesos distintos dentro de la misma fuente; varias adjudicaciones se conservan sin multiplicar la frecuencia.
- Las ventanas incluyen ambos extremos y usan 720/2.160 horas transcurridas. Se excluye todo el proceso objetivo, incluidas sus demás adjudicaciones y fallos de calidad.
- La identidad exige una unidad no ambigua, identificadores oficiales y fila de fuente. Los alias con espacios alrededor del identificador de proceso también se detectan antes del conteo.
- Una fecha de adjudicación ausente en otro proceso deja desconocido el conteo que podría afectar; no se sustituye por publicación ni se descarta porque su publicación sea antigua.
- Una categoría ausente afecta a reiteración. Una modalidad desconocida afecta a directas. Los indicadores conservan por separado su disponibilidad.
- La captura usa un diccionario de etiquetas exactas normalizadas, incluidas las variantes directa con/sin ofertas y las modalidades ya reconocidas por la referencia base. Una etiqueta que solo contenga «directa» no recibe una clasificación positiva automática. La clasificación de modalidad no valida el número de oferentes ni demuestra competencia efectiva.
- El constructor solo acepta conteos con la política `selected-source-capture-rolling-v1` y una identidad objetivo válida; no admite cantidades heredadas sin esa procedencia.

Los problemas de calidad se agregan primero por proceso y luego por par. Esto permite excluir el proceso objetivo sin borrar problemas de otros procesos. La consulta de cada lote utiliza uniones sobre tablas temporales indexadas; no ejecuta una búsqueda completa de historia por cada contrato.

## Importes y alcance temporal

La proyección raw actual no incorpora una moneda explícita. Se retiró el total sin denominación que antes exponía el diagnóstico. Ahora devuelve `amount=null`, `amounts_complete=false` y `moneda_no_documentada_en_fuente_local`. Los conteos pueden seguir siendo evaluables. La referencia monetaria v2 y su comparación SQL siguen disponibles para entradas que sí declaren moneda, sin inventarla en la captura.

El ancla de estas ventanas integradas es **el instante de captura del diagnóstico**. No se presenta como una reconstrucción de lo que se conocía al adjudicar un contrato antiguo. Las observaciones conservan `observed_at_capture_not_backdated` y la metadata identifica el ancla y el universo: pares con claves normalizadas conocidas en las fuentes seleccionadas.

La cobertura fuera de ese universo continúa sin comprobarse. Las filas sin claves no se asignan a un proveedor por nombre. La captura diaria normal sigue utilizando evidencia revisada de etapa; no se sustituyó por estos contextos actuales para entrenar modelos históricos.

## Comprobaciones integradas

Los 17 casos nuevos atraviesan `prepare_context`, `fetch_batch` y `build_observation`, comparando los conteos contra la referencia Python. Incluyen ceros, positivos, varias adjudicaciones, procesos con el mismo texto en fuentes distintas, alias, espacios en identificadores, fechas ausentes, categoría ausente, adjudicación ausente, fallos del propio proceso, modalidades desconocidas, modalidad competitiva, acentos Unicode descompuestos y límites temporales. También se comprobó el rechazo de conteos para un objetivo ambiguo y la independencia frente a la zona horaria de la sesión.

Una primera batería enfocada reveló un problema en el ensayo de terminación del trabajador en Windows: el lanzador del entorno virtual puede tener un PID distinto del intérprete que sostiene el bloqueo. Se corrigió el ensayo para terminar el PID confirmado del intérprete. La batería completa posterior, incluido ese ensayo, terminó sin fallos.

Se cargaron además las **13 proyecciones reales guardadas**, con 21 filas de ensayo, en la base aislada OID **82244**. Los conteos coincidieron en todos los casos. Los identificadores técnicos de fuente/fila se reasignaron para el ensayo; las fechas originales de publicación no estaban en esas proyecciones y quedaron nulas. Por ello esta prueba verifica integración sobre la proyección almacenada, no una réplica completa de raw ni sus filtros de publicación. La transacción se revirtió y se comprobó que no quedaron fuentes de ensayo. El [informe del piloto](MATERIALIZACION_VENTANAS_PILOTO_20261019.json) documenta este alcance.

## Límites y trabajo siguiente

Esta entrega cierra la integración de **conteos de 30/90 días** en la captura de diagnóstico local. No acredita el denominador anual de concentración de mercado, la semántica de oferentes, rendimiento a volumen completo ni suficiencia predictiva. Esos alcances deben evaluarse por separado.

El siguiente paso es combinar IQR y ventanas por operación, corte y alcance compatibles; revisar competencia y la cobertura anual; y repetir la sensibilidad sobre las familias corregidas. La publicación y los modelos siguen condicionados a las validaciones del plan. Los pesos históricos 1 / 1,5 / 2 y la referencia de un punto por familia no se modificaron, no hubo acceso a la base original en estas comprobaciones y no se contactó a terceros.
