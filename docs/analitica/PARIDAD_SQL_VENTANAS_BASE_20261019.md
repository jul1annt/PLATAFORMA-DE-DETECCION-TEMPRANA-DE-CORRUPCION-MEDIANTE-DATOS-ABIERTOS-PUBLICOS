# Comparación independiente de conteos móviles en SQL

Avance posterior: la [política monetaria v2 y el lote reproducible](IMPORTES_Y_LOTES_BASE_20261019.md) amplían esta comparación a agregados monetarios. Este documento conserva el alcance y la evidencia de la primera comparación de conteos y calidad; la equivalencia con el materializador anterior continúa pendiente.

## Entrega

`Backend/modules/motor_riesgo/rolling_sql_check.py` contrasta los conteos y motivos de calidad de la referencia Python con una agregación independiente en PostgreSQL. Ejecuta un único `SELECT` sobre el JSON suministrado: no crea tablas, no inserta registros ni consulta contratos operativos. SQLAlchemy está limitado al adaptador de validación; el dominio, el entrenamiento y la inferencia no reciben dependencias nuevas.

El comparador valida el contrato de entrada mediante la referencia existente, transporta identidades y fechas con los mismos ayudantes del dominio y calcula por separado en SQL agrupaciones, versiones contradictorias, exclusiones, conteos distintos y motivos de abstención. No reutiliza los conteos de Python como resultados SQL. Esta prueba demuestra concordancia entre agregaciones para las entradas ensayadas; compartir los ayudantes de normalización no constituye una segunda validación de la fuente o de sus identidades.

## Comprobaciones

Pasaron **120 pruebas enfocadas**: las 88 anteriores de cobertura, IQR y ventanas, más 32 del comparador SQL. Dentro de estas últimas se comparan 100 marcos mixtos con semilla fija `20261019`, además de 31 casos fijos, en una base PostgreSQL de pruebas local. Es una batería enfocada, no una nueva ejecución completa del backend.

Los casos incluyen señales positivas —tres procesos previos—, procesos de distintas fuentes con el mismo texto, varias adjudicaciones por proceso, copias exactas, versiones contradictorias, identidades inválidas, métodos no verificados, categorías ausentes, historia incompleta, fechas inválidas y eventos futuros. Se contrastan tanto el conteo completo como las observaciones parciales y cada motivo de abstención.

Las ventanas de la referencia son duraciones transcurridas de **720 y 2.160 horas**, equivalentes a 30 y 90 días de 24 horas, entre instantes normalizados a UTC. El SQL utiliza horas explícitas para conservar esa definición cuando el servidor cambie de zona. Se probaron `UTC`, `America/Bogota` y `America/New_York`, incluyendo el intervalo que atraviesa un cambio de horario estacional. Los límites siguen siendo inclusivos y el proceso objetivo se excluye antes de evaluar fechas.

## Contraste con archivos SECOP reales

También se compararon las **13 historias de pares locales** adquiridas en el piloto anterior. La comprobación se ejecutó en una transacción de solo lectura sobre la base aislada con OID **82244**, usando los JSON guardados, sin volver a consultar la base original ni insertar sus filas en la de pruebas.

Los 13 marcos coincidieron en conteos, observaciones y motivos de calidad. Tardaron aproximadamente **0,093 segundos** en esa ejecución. Todos esos conteos reales eran cero; por ello los ensayos sintéticos con positivos son necesarios para comprobar las rutas de detección. Estos tiempos y resultados no constituyen una medición de rendimiento del procesador sobre nueve millones de filas.

El [informe de comparación](COMPARACION_SQL_VENTANAS_PILOTO_20261019.json) conserva cada resultado y hashes. El recibo `VALIDACION_PARIDAD_SQL_VENTANAS_20261019.json` enlaza la batería, el código y el piloto. Las entradas reales siguen en el directorio privado local.

## Límites y siguiente integración

- La concordancia comprobada cubre **conteos y motivos de calidad**. No se compararon sumas monetarias, conversiones de moneda o justificaciones documentales.
- El universo real continúa limitado a las claves del corte normalizado local; no se resolvieron identidades fuera de él ni se reconstruyó conocimiento histórico de etapa.
- El materializador anterior `history.py` usa tablas temporales y reglas diferentes, incluida una búsqueda textual de modalidad directa. **Esta comparación no acredita equivalencia con ese materializador.** El informe devuelve expresamente `legacy_history_parity_checked=false`.
- El adaptador nuevo valida marcos suministrados; no es un sustituto escalable del extractor operativo. Antes de reemplazarlo deben trasladarse las reglas comprobadas al procesamiento por lotes, verificar cobertura y reconciliación de identidad, y medir recursos en la copia aislada.
- No se conectaron estos conteos a la publicación ciudadana. Falta combinar resultados por identidad, corte y alcance compatibles y verificar los campos de competencia.

Esta entrega añade una referencia SQL comprobable para desarrollar el motor. No modifica coeficientes, la referencia de un punto por familia, modelos o el corte publicado; no incorpora una calibración predictiva ni una probabilidad de corrupción.
