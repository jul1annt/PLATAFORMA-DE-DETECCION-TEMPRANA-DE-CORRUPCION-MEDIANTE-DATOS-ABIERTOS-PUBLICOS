# Operar el resumen transaccional de calidad

Estado: **`794d185` activado y verificado en la base canónica, esquema `3c19a8f7e2d0`**, con perfil aceptado por el usuario. El resumen coincide con el agregado independiente de 9.249.545 contratos y sus cuatro triggers están habilitados. Pasaron 19 comprobaciones HTTP/worker y 9.083/9.083 lecturas correctas con ocho clientes, búsqueda p95 0,283 s y calidad 0,0048 s. [Despliegue, evidencia reutilizada e incidentes conservados](ACTIVACION_LOCAL_VERIFICADA_20261012.md). Las instrucciones siguientes describen preparación, verificación y reversa para cambios posteriores; este corte no necesita otra carga o inicialización del resumen.

## Preparación

1. Usar el alcance local elegido por el usuario el 2026-10-11 y adjuntar los gates nativos del artefacto exacto, con las comprobaciones reutilizadas identificadas. Completar perfil conjunto, aceptación y comprobaciones de recuperación antes del despliegue. Conservar respaldo/control checkpoint, credenciales, revisión y artefactos anteriores según [la guía de integración](INTEGRACION_LOCAL.md).
2. Cerrar servicios, comprobar fuentes pausadas, ausencia de trabajos/escritores activos y OID/puerto/rol del destino. La revisión previa al resumen es `08c6d9a2e4b1`; el nuevo backend debe incorporar el `COUNT(*)` compatible con el índice compacto antes de retirar el anterior. No aplicar ciegamente a la base publicada desde un script de pruebas.
3. Aplicar la migración `2ab7c4e8d910` con aislamiento `read committed`. Inicializa una fila por un único agregado sobre contratos existentes; no requiere extracción, transformación o restauración del universo. La espera por bloqueo y el conteo son acotados a 5 s/120 s solo en la transacción. Si falla, inspeccionar la revisión realmente confirmada: el predecesor compacto puede haber cerrado antes. Reanudar desde esa revisión; no borrar contratos ni iniciar un bucle de recarga.
4. Verificar fila id=1, los cuatro triggers habilitados y contadores iguales al agregado de referencia. Reiniciar con sesiones nuevas y registrar el estado real en los manifiestos del despliegue. Mantener las opciones de paralelismo de lectura omitidas durante la primera comparación.

El índice compacto y el resumen son cambios distintos: el primero modifica un índice; el segundo añade contadores/triggers. El resumen no requiere borrar ese índice y no altera identidades, valores de contratos o collation.

El candidato actual añade además `3c19a8f7e2d0`: un índice concurrente de fecha e ID para el desempate estable de páginas. Puede reanudar su aplicación si el índice existente coincide y está válido/listo; un objeto distinto o inválido se conserva para inspección. Su downgrade retira únicamente ese índice verificado. El índice ocupa unos 278,25 MiB en la copia completa y añade coste a las escrituras; incluirlo en el perfil real, junto con los deltas del resumen. No necesita recargar ni normalizar contratos.

## Cotejo independiente

Ejecutar solo cuando la migración esté aplicada. Esta consulta es de lectura, utiliza una sola instantánea y devuelve igualdad exacta de los contadores; no reconstruye ni modifica filas:

```sql
SELECT
  (s.total,s.incompletos,s.sospechosos,s.alto_riesgo,s.con_confianza,s.suma_confianza)
  IS NOT DISTINCT FROM
  (d.total,d.incompletos,d.sospechosos,d.alto_riesgo,d.con_confianza,d.suma_confianza)
  AS coincide
FROM public.contratos_metricas_calidad s
CROSS JOIN (
  SELECT count(*) AS total,
         count(*) FILTER (WHERE es_incompleto IS TRUE) AS incompletos,
         count(*) FILTER (WHERE es_sospechoso IS TRUE) AS sospechosos,
         count(*) FILTER (WHERE clasificacion_riesgo='ALTO') AS alto_riesgo,
         count(nivel_confianza) AS con_confianza,
         coalesce(sum(nivel_confianza::numeric),0) AS suma_confianza
  FROM public.contratos_procesados
) d
WHERE s.id=1;
```

La respuesta esperada es una fila `true`. Ausencia de fila, `false`, trigger ausente/deshabilitado o error deben investigarse; no resolverlos vaciando la base o refrescando contadores sin comprobar la causa.

## Medición y reversa

Calidad, tablero y distribución de anomalías leen el resumen. Las otras consultas conservan su estrategia. Antes de aceptar rendimiento, medir el corte completo con el perfil HTTP exigido, cuerpo de respuestas, recursos, procesamiento concurrente, recuperación y exclusión de workers. Los ensayos sintéticos añadieron coste a cambios de confianza; la fila única también serializa esos escritores. Mantener lotes existentes y medir operaciones masivas: los triggers por sentencia de INSERT/DELETE reciben las filas afectadas en relaciones de transición.

Los cambios de fecha o datos que no contribuyen a métricas no actualizan contadores. INSERT/DELETE/UPDATE/TRUNCATE mantienen el resumen dentro de la misma transacción, incluidas escrituras SQL ajenas al ORM si los triggers están habilitados. No deshabilitarlos ni escribir contadores manualmente en la base operativa.

Para una reversa planificada, cerrar servicios y conservar evidencia. El downgrade a `08c6d9a2e4b1` elimina solo resumen, funciones y triggers, conservando contratos e índice compacto; el repositorio retorna al agregado directo al abrir una sesión nueva sin la tabla. Verificar SQL/HTTP, datos, fuentes y cola. La reversa del índice es independiente y exige comprobar el backend compatible. Una restauración debe usar un destino aislado y el estado del respaldo, seguido de migraciones/cotejos; no mezclar datos de un dump y contadores de otra generación.
