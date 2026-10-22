# Revisión 15: fases e identidad de Centros Poblados

El CAPTCHA de SECOP II se resolvió con autorización expresa. La consulta pública del aviso `CO1.NTC.1465671` muestra la fase de oferta del proceso `FTIC-LP-038-2020` y enlaza la fase previa `CO1.NTC.1393216`, guardada en el corte local. La página contiene dos lotes: REGIÓN A y REGIÓN B. El presupuesto total del proceso no debe confundirse con el valor adjudicado de uno de los lotes.

## Evidencia y límites

- La consulta indexada y de solo lectura en la copia aislada OID 75045 devuelve una fila del proceso `CO1.REQ.1439880`: raw 2307014, sin adjudicación. No identifica por sí misma la operación del contrato 1043.
- La consulta exacta de la fuente oficial actual devuelve el mismo proceso con otro ID de fila: `row-ne3d.eun6-zx28`, frente a `row-5jmz.ur5e.ad74` guardado. Se conservan ambas observaciones; no se asignan alias, causa del cambio ni identidades al legado.
- La página de oferta incorpora un informe de selección de mayo de 2022, `CO1.AWD.1272856`. No se atribuye automáticamente a la adjudicación investigada de 2020 ni se utiliza como información disponible entonces.
- Se localizaron estudios, pliegos y resolución de apertura en el listado público. La herramienta de navegación denegó la descarga por falta de aprobación de descarga del sitio. No se intentó obtener el archivo por una vía alternativa después del rechazo. Los documentos siguen como localizados, no adquiridos ni revisados físicamente.
- Las fechas del cronograma no se convierten en fechas reales de celebración. La lectura de una página actual tampoco acredita la disponibilidad histórica de cada campo.

El [informe estructurado](IDENTIDAD_SECOP_CENTROS_POBLADOS_20261019.json) conserva los resultados y hashes de las consultas. El [inventario 15](INVENTARIO_CASOS_REVISION15_20261019.json) y su [cobertura](COBERTURA_CORPUS_REV15_20261019.json) se recalcularon con el validador vigente: **14 candidatos, cero aptos**. No se añadieron etiquetas ni observaciones históricas, no se entrenó y no hubo escrituras de base de datos.

No cambió código productivo en esta revisión. No se repitió la batería de pruebas: el último resultado completo continúa siendo 674 pruebas backend aprobadas en la revisión anterior. La comprobación actual valida los hashes de las consultas, conserva el registro anterior por hash y recalcula la exclusión del corpus.

## Trabajo pendiente

Obtener los originales judiciales y su firmeza documentada, determinar la adjudicación exacta y reconstruir la evidencia de cada etapa antes de la investigación. La suficiencia de expedientes independientes y las validaciones de los dos modelos siguen pendientes; la nueva publicación continúa desactivada.
