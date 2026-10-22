# Base analítica: estratos contractuales y cobertura de vínculos

## Trabajo realizado

Se añadió un análisis desconectado por año de publicación, modalidad y segmento UNSPSC. Su unidad es una adjudicación identificable en resultados contractuales legados; **no** se trasladó a cada contrato la puntuación agregada de su proveedor.

La selección reproducible tomó resultados de la ejecución IQR `4e677b91-c0df-4a20-8f3a-b114b5beb382` en dieciséis intervalos UUID de igual ancho, uno por cada primer dígito hexadecimal, con semilla `20261019`. Cubren 1/1024 del espacio UUID. No se seleccionaron por puntuación ni nombre. El supuesto de uniformidad de UUID permite una exploración dispersa, pero no garantiza representación de cada sector o modalidad; no se presenta como censo ni se publican estimaciones poblacionales de corrupción.

Se obtuvieron **841 resultados**, todos con identificadores SECOP y adjudicación informada en la fuente. Los metadatos se consultaron en el corte local actual; no son una reconstrucción de lo conocido en convocatoria. No se extrajeron nombres o NIT. Las comprobaciones de igualdad de claves de entidad/proveedor se hicieron dentro de SQL y no se exportaron esas claves.

## Identidad y cobertura

La búsqueda en la fuente local encontró:

| Comprobación | Cantidad |
| --- | ---: |
| Resultados seleccionados | 841 |
| Adjudicaciones con una sola fila para la identidad exacta consultada | 510 |
| Resultados con al menos dos filas de la misma identidad | 331 |
| Resultados IQR disponibles entre las 510 unidades retenidas | 510 |
| Señales IQR legadas entre esas unidades | 52 |
| Unidades retenidas con reiteración observada y vínculo comprobado | 24 |
| Reiteración sin observación admisible para esta comparación | 486 |

La identidad usa fuente, proceso y adjudicación con su escritura exacta, además del identificador de fila para trazabilidad. Se excluyen todas las filas de una unidad repetida, incluso si aparecen varias dentro de la selección. Se conservan adjudicaciones distintas de un mismo proceso. No se asignan identidades a registros antiguos ni se infieren equivalencias por nombres.

Los pares de reiteración requieren procesos distintos, misma fuente, claves conocidas e iguales de entidad/proveedor, fechas coherentes con los contratos enlazados y una separación de 0 a 30 días. Se utiliza exclusivamente el resultado del par vinculado a ese contrato. La falta de par comprobado queda como **desconocida**, no como cero. Estas comprobaciones no confirman identidad ante DIAN ni reconstruyen un expediente judicial.

Las 510 unidades son aptas **solo para este análisis descriptivo de identidad y cobertura**. No son casos judiciales aptos para entrenar. Las 52 señales proceden del IQR legado guardado, cuyas agrupaciones son distintas de las reglas corregidas; no son 52 hechos de corrupción ni resultados nuevos del motor candidato.

## Desglose obtenido

Ejemplos de los grupos de mayor tamaño; el informe conserva todos los grupos y categorías ausentes:

| Dimensión | Grupo | Unidades retenidas | Con ambos componentes observados |
| --- | --- | ---: | ---: |
| Año de publicación | 2023 | 83 | 5 |
| Año de publicación | 2024 | 74 | 7 |
| Año de publicación | 2022 | 63 | 0 |
| Modalidad | Mínima cuantía | 296 | 11 |
| Modalidad | Contratación directa con ofertas | 65 | 7 |
| Modalidad | Selección abreviada de menor cuantía | 47 | 2 |
| Segmento UNSPSC | 80 | 50 | 2 |
| Segmento UNSPSC | 72 | 48 | 3 |
| Segmento UNSPSC | 81 | 43 | 1 |

El año corresponde a publicación normalizada, no a adjudicación o sentencia. El segmento UNSPSC se extrae del formato de ocho dígitos; no es un sector institucional ni una clasificación económica del proveedor. Las 22 unidades sin código con formato verificable se conservan en su categoría de cobertura, sin asignarles un sector inferido.

## Resultado de las comparaciones

El módulo puede comparar puntuación IQR y reiteración legadas observadas, separando el efecto de acotar escalas y el de igualar pesos, con empates fraccionarios y correlaciones de rangos. La comparación usa únicamente filas con ambos componentes disponibles y exige al menos 30 unidades por grupo como mínimo operativo, sin afirmar suficiencia estadística.

**En los datos reales de esta selección, todas las comparaciones conjuntas se abstienen:** hay 24 unidades completas en total y menos en cada estrato. No se rellenaron las otras 486 con cero, no se redujo el mínimo para obtener cifras y no se reutilizó la referencia de proveedores como si fuera una referencia contractual. La estabilidad global por proveedor previamente calculada sigue siendo válida únicamente para su marco original de 31.731 resultados.

## Optimización de las lecturas

La consulta inicial que combinaba toda la selección, identidad y pares agotó 30 segundos y fue cancelada. Dividirla en lotes de cien no resolvió todas las lecturas. Los recuentos globales agrupados de alias, incluso reduciendo el lote, también agotaron su límite de diez segundos. Esos intentos se registran como fallos, no como verificaciones correctas.

La implementación final separó responsabilidades:

1. Selección mediante rangos de la clave primaria y metadatos, con máximo de 12.000 resultados; se rechaza una selección truncada.
2. Identidad por consulta exacta con `LIMIT 2`: dos coincidencias bastan para declarar ambigüedad; no se cuentan todas las copias.
3. Pares de reiteración consultados por lotes de cincuenta contratos y comprobados antes de exportar su puntuación.

La selección y los metadatos tardaron 14,16 segundos; la comprobación acotada de identidades y pares, 18,94 segundos. Son fases separadas y tiempos observados, no una garantía de duración futura ni una comparación de rendimiento controlada. Se mantuvieron consultas de solo lectura, límite de diez segundos por sentencia en los lotes, memoria de trabajo de 16 MiB y ejecución sin paralelismo de la consulta. No se añadieron índices, ejecutaron recargas o modificaron tablas publicadas.

## Código y reproducción

- `Backend/modules/motor_riesgo/contract_strata.py`: validación de identidad, cobertura y estratos, exclusiones y comparaciones cuando hay datos suficientes.
- `Backend/scripts/risk_contract_strata.py`: diagnóstico desconectado, entrada limitada a 16 MiB y 12.000 registros, salidas nuevas y hashes de entrada/código.
- `Backend/tests/test_contract_strata.py`: identidades ambiguas, adjudicaciones múltiples, fuentes distintas, datos desconocidos, abstención y protección frente al traslado de puntuaciones de proveedor.

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_contract_strata.py --input Backend/.codex-analytics-postgres/contract-strata-input-20261019.json --output estratos-nuevos.json
```

Las entradas y los planes de adquisición quedan en el directorio privado. El [informe agregado](ESTRATIFICACION_CONTRACTUAL_20261019.json) y la [validación con hashes](VALIDACION_ESTRATIFICACION_CONTRACTUAL_20261019.json) no incluyen puntuaciones por persona. La reproducción desconectada coincidió exactamente con el informe conservado.

Pasaron **81 pruebas enfocadas**, con conjuntos superpuestos a las comprobaciones anteriores. No se repitió la batería general del backend para estos módulos nuevos de laboratorio. Se comprobaron de nuevo esquema, pesos y referencia del despliegue original. No hubo entrenamiento, contacto con terceros o cambio de publicación.

## Qué queda

Avance posterior: el [primer grupo completo con IQR corregido](REGLAS_CORREGIDAS_CORTE_2017_20261019.md) utiliza una referencia de 1.392 unidades identificadas y evalúa todas sus 1.698 filas. No utiliza la muestra de 841 filas como referencia IQR ni convierte sus metadatos actuales en información histórica.

La herramienta de estratificación y su control de cobertura están implementados. Para concluir sobre estabilidad conjunta por sector, modalidad o periodo faltan suficientes unidades con componentes comprobados en cada grupo. El siguiente desarrollo debe construir observaciones de las familias corregidas con identidades y denominadores explícitos, conservando por separado los análisis descriptivos del corte y los datos históricos admitidos para entrenamiento. La escasez de pares comprobados de este legado no se resolverá propagando riesgo del proveedor o tomando registros sin etiqueta como negativos.
