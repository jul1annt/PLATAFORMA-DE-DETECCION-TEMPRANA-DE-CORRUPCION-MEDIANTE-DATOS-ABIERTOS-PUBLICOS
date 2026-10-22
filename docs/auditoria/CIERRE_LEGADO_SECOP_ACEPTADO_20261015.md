# Cierre local de P05/P12 con limitación histórica aceptada

El usuario aceptó **«Aceptar la limitación histórica»** el 15/10/2026. El [alcance aceptado](LIMITE_HISTORICO_SECOP_ACEPTADO_20261015.md) conserva los criterios originales y documenta su sustitución. **P05 y P12 cierran como investigación con legado no conciliado.** Las identidades oficiales anteriores siguen sin demostrarse para las **18.980 filas**; no se declara conciliación histórica completa.

## Comprobación del original y del detalle individual

Se confirmó en una transacción `REPEATABLE READ, READ ONLY` el original `plataformaanticorrupcion_pre_20261010`, puerto 5432, OID **17930**, revisión `c7e3a91b5d24`, sin otros clientes conectados. Sus **18.980 IDs locales** coinciden exactamente con los del informe individual, sin omisiones ni duplicados. La columna Socrata sigue ausente. La huella de las primeras 2.000 filas coincide con la evidencia anterior; se añadió una huella de toda la tabla actual como referencia de conservación, sin atribuirle una identidad histórica recuperada.

El archivo individual conserva **10.145.604 bytes** y SHA-256 `4cb38055eecad6453659c4e1d9cc193202236dcd139538f025107fbfa7c8f0d3`. Cada caso sigue marcado como identidad anterior no demostrada. Las listas de candidatas están limitadas a 20; sus cardinalidades representan todas las coincidencias.

| Clasificación alternativa | Única | Ambigua | Ausente | Total |
| --- | ---: | ---: | ---: | ---: |
| Coincidencia exacta de contenido, corte 01/10 | 15.392 | 118 | 3.470 | 18.980 |
| Tupla diagnóstica de adjudicación, corte 01/10 | 18.115 | 157 | 708 | 18.980 |

Las dos clasificaciones no se suman; el corte del 30/09 conserva sus resultados separados. Una coincidencia de contenido no se convierte en identidad oficial anterior. Los **18.980 registros antiguos permanecen como legado no conciliado**.

## Conservación y versionado

El original y la base publicada tienen OIDs distintos (**17930** y **24577**). Se confirmó la identidad publicada `plataformaanticorrupcion:5432`, revisión `3c19a8f7e2d0`, con fuentes y trabajos activos en cero. Su tabla de historial existe y el trigger `trg_archive_raw_secop_version` está habilitado. Se registraron las huellas de las definiciones actuales sin ejecutar actualizaciones de prueba.

Se reutiliza la medición aislada de **6.000 versiones sobre 2.000 registros**: crecimiento de 12.730.368 bytes, **2.121,728 bytes por versión**, y cero versiones ante un cambio solo de fecha de sincronización. Es evidencia histórica de una muestra; no es una prueba nueva de rendimiento a escala ni reconstruye cambios anteriores al versionado.

Los **ocho respaldos históricos protegidos** siguen presentes y con el tamaño registrado. Se reutilizan sus comprobaciones criptográficas/restauraciones previas, sin volver a leer o restaurar todos los dumps grandes. El respaldo pequeño específico del original, `publication-20261010/operational-before.dump`, sí se volvió a comprobar completo: **6.374.617 bytes**, SHA-256 `2d775be9bdb6f768dbd96d0a99d3368dee166d566095ab6c6d9e8894931981f8`. La política conservadora aprobada continúa vigente.

La línea de base publicada sigue siendo el corte histórico del **01/10/2026**. El historial futuro recogerá solo cambios efectivamente observados por el mecanismo vigente. No se afirma captura continua desde esa fecha; las fuentes siguen pausadas y no se inventan versiones de intervalos no capturados.

**Cero escrituras SQL, cero IDs oficiales asignados, cero respaldos eliminados, sin recarga ni reproceso histórico.** El historial público visible se consultó en modo de lectura y no proporcionó una versión archivada para recuperar IDs anteriores. [Constancia previa de disponibilidad](DISPONIBILIDAD_HISTORICA_SECOP_20261015.json).

## Estado del plan

**100/101 completados (99,0 %); P01 es el único pendiente.** P01 requiere aplicar con privilegios administrativos las seis reglas ya autorizadas y verificar el tráfico real. Este cierre acepta la limitación histórica; no convierte las identidades desconocidas en identidades verificadas.

[Informe estructurado, hashes y alcance de cada comprobación](CIERRE_LEGADO_SECOP_ACEPTADO_20261015.json).
