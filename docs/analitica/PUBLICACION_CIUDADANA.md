# Cortes ciudadanos coherentes y reversibles

Implementación candidata local. El despliegue publicado mantiene su versión anterior y el corte del **01/10/2026**. No hay modelos judiciales reales aprobados ni programación nueva activada.

## Preparación y publicación

`POST /api/riesgo/admin/preparar-base` requiere autenticación y devuelve **202**. Encola un trabajo durable con clave única `riesgo:base-ciudadana`; no calcula agregados dentro de la solicitud HTTP. La recuperación reutiliza un UUID determinista por trabajo y la revisión originalmente congelada.

El trabajador prepara una revisión de contratos normalizados, hallazgos de calidad, resumen de métricas y estadísticas de campos faltantes. Solo cambia el puntero inicial cuando están listos sus agregados. No crea modelos, no habilita fuentes y no activa la actualización diaria.

Las escrituras posteriores conservan imágenes anteriores únicamente de filas modificadas o eliminadas en `riesgo_historial`. Las filas nuevas se identifican por su revisión. Las vistas de `riesgo_ciudadano` reconstruyen los intervalos de vigencia. No se clona diariamente la tabla de nueve millones de contratos. `TRUNCATE` se rechaza para impedir la pérdida de versiones necesarias para una reversa.

Un bloqueo breve de escritura sobre las cuatro tablas espera las transacciones anteriores y fija la revisión. Las consultas ciudadanas continúan disponibles. Los agregados costosos se calculan fuera de ese bloqueo y se conservan con revisión, cobertura y SHA-256. La distribución y los principales proveedores se leen del resultado persistido; no vuelven a agrupar todo el universo por solicitud.

Para publicar un corte analítico se comprueban los dos modelos, la cobertura total, la cobertura evaluable, la firma del origen y la revisión ciudadana. El certificado conserva los hashes exactos del modelo y su informe de aprobación. Los dos punteros, el estado publicado y la auditoría cambian en **una misma transacción**. Si faltan agregados válidos o solo hay abstenciones, se conserva el corte anterior. Un candidato que quedó obsoleto pausa la programación y requiere revisión explícita.

## Lecturas y paginación

Las respuestas ciudadanas exponen `X-Public-Cut` y `X-Data-Cut-At`; `X-Public-Cut` también permite solicitar una versión anterior. Listado, tablero, detalle, hallazgos, métricas, exportaciones e índice reutilizan la misma versión. Cada solicitud restaura su configuración de lectura al finalizar. La interfaz no añade un índice nuevo a datos que llegaron sin versión.

La paginación ordena y limita las ramas actual e histórica antes de unirlas. Para un desplazamiento `k` y tamaño `n`, cada rama aporta como máximo `k+n` filas con los mismos filtros y orden total, incluyendo ID para resolver empates. Después se aplica el orden y desplazamiento global. Así se evita ordenar todo el universo para una primera página. Las páginas profundas conservan un coste creciente; no se afirma que `OFFSET` sea constante.

Las exportaciones en cola guardan el identificador del corte y lo recuperan en el trabajador. Los controles administrativos de calidad tienen rutas autenticadas para consultar el estado operativo actual.

## Reversa

`POST /api/riesgo/admin/revertir/{cut_id}` restaura juntos los datos ciudadanos y los resultados de un corte publicado, y pausa la programación diaria. Verifica sus agregados y el certificado de aprobación conservado. Sirve resultados ya persistidos sin ejecutar un modelo antiguo: una actualización incompatible del constructor de variables no impide consultar una publicación anterior íntegra. La activación y la inferencia nuevas siguen exigiendo la versión actual.

## Evidencia y límites

Las pruebas cubren ediciones, inserciones, eliminaciones, nulos, empates, filtros, exportaciones, fallos después de asignar punteros, alteraciones de artefactos y reversa después de cambiar la versión de variables. Dos lectores hicieron 48 consultas mientras se confirmaban ocho actualizaciones reales en la base de pruebas: todas conservaron el corte fijado.

La [medición HTTP](RENDIMIENTO_LECTURA_CIUDADANA_20261016.json) conserva los tres ensayos sobre la copia aislada de **9.249.545 contratos**. El último completó 29 solicitudes sin errores, incluidas 20 concurrentes, con percentil 95 de **0,03379 s**. La primera página tardó **0,47857 s**, la distribución **0,00514 s** y los principales proveedores **0,00865 s**. La preparación única de agregados tardó **39,79306 s** y conservó las revisiones y recuentos de origen.

Son tiempos observados con estados de caché diferentes, no una comparación controlada de almacenamiento frío. El ensayo no incluye inferencia ni persistencia completas del índice, revisión predictiva real, memoria máxima o recuperación del paquete operativo completo. La base publicada no participó en estas escrituras.
