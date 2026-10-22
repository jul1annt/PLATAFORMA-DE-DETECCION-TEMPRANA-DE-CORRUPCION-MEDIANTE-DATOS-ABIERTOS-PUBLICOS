# Contabilidad de la separación cronológica

## Fallo corregido

La separación por fechas y expedientes puede excluir filas cuando un expediente desplaza una frontera y deja operaciones fuera de su bloque asignado. La aprobación exigía que la suma de los tamaños de entrenamiento, ajuste y evaluación fuera igual al total de filas verificadas antes de esa separación. Un modelo con exclusiones temporales legítimas quedaba rechazado incluso después de superar los demás criterios.

Se conservan las fronteras, el agrupamiento por expediente y la conversión a «sin etiqueta» de positivos cuya decisión aún no estaba disponible. La corrección incorpora la contabilidad explícita de esas operaciones.

## Manifiesto de partición

La política `chronological-grouped-label-availability-v1` genera `split_audit`, con:

- Total de entrada y tamaños de los tres bloques.
- Filas excluidas y motivo: expediente fuera de su bloque cronológico asignado.
- Etiquetas futuras tratadas como desconocidas, por bloque.
- Fronteras de operación y fechas límite de disponibilidad de etiquetas.

El artefacto conserva `split_audit_sha256`; el informe incluye la auditoría completa. La aprobación comprueba su integridad y la igualdad **entrada = filas usadas + filas excluidas**. También verifica tipos y valores de los recuentos, coherencia de fronteras y que el número de expedientes positivos no exceda el número de filas de cada bloque.

Las etiquetas futuras permanecen en la población sin etiqueta; no se eliminan usando el conocimiento posterior de su desenlace. Se mantienen los mínimos de cinco expedientes independientes por bloque, los intervalos por expediente y la comparación con reglas, incluida la evaluación con proveedores no vistos. El nuevo informe es requisito de aprobación; el entrenamiento lo genera automáticamente. No se migraron modelos operativos, porque no existen modelos judiciales reales aprobados.

## Validación

La [validación consolidada](VALIDACION_PARTICIONES_TEMPORALES_20261019.json) registra **606 pruebas aprobadas**, cero fallos, errores u omisiones. Incluye un entrenamiento sintético reproducible cuya partición excluye una fila y supera la comprobación de aprobación con su auditoría enlazada. Los informes ausentes, alterados o incoherentes son rechazados.

Después se comprobaron mediante lectura la base aislada OID 82244 —sin modelos ni evidencias de variables persistidos— y la base publicada OID 24577, que conserva esquema `3c19a8f7e2d0` y no tiene las nuevas tablas de publicación. No se repitieron migraciones ni cargas de volumen.

No cambiaron el código de predicción, las dependencias de API, el lock de entrenamiento o las dependencias de inferencia. Cambiaron entrenamiento, evaluación y aprobación, con hashes en el manifiesto de cada entrenamiento futuro. Las pruebas acreditan software y datos sintéticos; no acreditan eficacia con corrupción real. El inventario conserva once candidatos y cero aptos.
