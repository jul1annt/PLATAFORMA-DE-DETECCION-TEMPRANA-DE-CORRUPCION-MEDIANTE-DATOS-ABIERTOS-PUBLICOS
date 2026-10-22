# Evidencia física de variables históricas

Política: `reviewed-physical-stage-evidence-v2`.

## Registro y revisión

Una observación no se vuelve verificable por declarar un SHA y una fecha en un JSONL. Para entrenar, administración registra una revisión con `POST /api/riesgo/admin/evidencias-variables`, cuerpo `{"record": {...}}`. La tabla `riesgo_evidencias_variables` conserva el contenido completo, su SHA, administrador y fecha del registro. No hay ruta para sobrescribir revisiones; una corrección requiere otro identificador.

El registro contiene:

- `evidence_id`: identificador de revisión, de 1–100 caracteres alfanuméricos, punto, guion o guion bajo.
- `observation`: observación completa sin `feature_evidence_id`. Debe identificar fuente, fila oficial, proceso y adjudicación cuando corresponda. El adaptador actual no puede verificar lotes. El registro administrativo contrasta la identidad con la fuente guardada.
- `review`: cuatro confirmaciones humanas explícitas: `dates_verified`, `values_verified`, `identity_verified`, `stage_verified`, todas verdaderas. El revisor debe comprobarlas antes de enviar el registro.
- `documents`: documentos físicos preservados dentro de `RISK_WORK_DIR/evidence`. Cada uno tiene `document_id`, `file` relativo, `sha256`, `url` oficial HTTPS, `available_at` y `temporal_basis`.
- `field_evidence`: una entrada por campo de la observación, con `document_ids`, `locator` preciso de página/sección/campo, y `value_sha256` del valor extraído.

Si se incluyen importes, se requiere además `review.monetary_basis_verified=true`. Cada campo monetario no nulo debe declarar la moneda, unidad, base de precios, significado del importe y transformación descritos abajo. El hash por sí solo no acredita su comparabilidad.

Un documento puede tener como base temporal `ORIGINAL_DATED_DOCUMENT`, cuya fecha y carácter original debe confirmar el revisor, o `CAPTURE_LOG`, que añade `captured_at`. Una captura no puede declararse disponible antes de haberse observado. No se aceptan documentos ausentes, modificados, mayores de 64 MiB ni rutas fuera del directorio de evidencia.

## Vinculación de campos

Cada campo conserva `value`, `available_at` y `sha256`; opcionalmente `event_at`. Su SHA es el resumen canónico del mapa `{document_id: sha256_del_documento}` de las fuentes que cita su revisión. `value_sha256` es el resumen canónico de `value`. Ambos usan `modules.motor_riesgo.domain.digest`: JSON UTF-8, claves ordenadas, separadores compactos y sin NaN.

Los documentos deben estar disponibles antes del campo, y el campo antes de la predicción. Las observaciones para este protocolo usan `temporal_scope=historical_stage_snapshot` y `stage_event_at=prediction_at`: reconstruyen un momento de etapa concreto. Este requisito no transforma capturas actuales en historia. Los positivos, además, deben ser anteriores a la primera investigación documentada.

## Base monetaria explícita

La política v2 admite en los importes predictivos únicamente **pesos colombianos nominales**, con importe original positivo y finito. `log_presupuesto` requiere `measure=PRESUPUESTO_PROCESO`; `log_adjudicado`, `measure=VALOR_ADJUDICADO`. No se intercambian estos conceptos. La moneda y unidad son `COP` y `PESOS`, la base `NOMINAL` y la transformación `LOG1P`.

El campo incorpora un objeto `monetary`, por ejemplo este fragmento sintético para un presupuesto de mil pesos:

```json
{
  "value": 6.90875477931522,
  "monetary": {
    "raw_amount": "1000",
    "currency": "COP",
    "unit": "PESOS",
    "price_basis": "NOMINAL",
    "measure": "PRESUPUESTO_PROCESO",
    "transform": "LOG1P"
  }
}
```

Es un fragmento, no un registro admisible completo. `raw_amount` se preserva como texto decimal; el validador comprueba `value=log1p(raw_amount)` con tolerancia relativa de 1e-12. La entrada correspondiente de `field_evidence` añade `monetary_sha256=digest(monetary)` y `monetary_locator`, que señala dónde se verificaron moneda, unidad, base y significado en los mismos documentos citados. La revisión y sus hashes quedan enlazados al contenido íntegro de la observación.

Se rechazan VPIT, pesos constantes, millones de pesos declarados como pesos, monedas extranjeras, conversiones implícitas y transformaciones incoherentes. No se incorporaron tasas de cambio o deflactores ni se inventan conversiones. La [resolución de Ruta del Sol](CORRESPONDENCIA_SECOP_RUTA_SOL_20261019.md) es un caso real de VPIT que debe permanecer fuera de esta escala aunque su número coincida con la cuantía actual de SECOP.

Omitir un campo monetario permite conservar evidencia válida de otros campos. El modelo se abstiene si faltan sus variables esenciales. No se declara una señal negativa por esa abstención. Esta política regula la admisión y revisión, compartidas por entrenamiento e inferencia; la fórmula de variables `secop-point-in-time-v3` permanece igual. La aprobación exige la política nueva y no acepta como equivalentes los informes con política v1.

## Uso en inferencia por etapa

La versión `secop-point-in-time-v3` exige la política `reviewed-stage-landmark-v1` tanto al validar el artefacto como al inferir. Una captura actual conserva sus valores y motivos de calidad, pero produce **abstención**: no sustituye el estado original de convocatoria o adjudicación.

El registro exige además `raw_secop_id` explícito y comprueba que coincide con la fila identificada por fuente, fila oficial, proceso y adjudicación. La fecha de predicción debe coincidir con la fecha conservada de la etapa. No se asignan identidades al legado. Las revisiones anteriores sin las nuevas columnas de identidad quedan preservadas, pero no se incorporan automáticamente a la inferencia.

La extracción consulta revisiones mediante un índice por fila y etapa, únicamente para el lote actual de 1.000 registros y registradas antes de la captura. Vuelve a comprobar documentos físicos, hash del registro, fechas e identidad. Dos revisiones idénticas son equivalentes; valores diferentes o una revisión inválida impiden usar esa etapa. Un límite de 20.000 revisiones por lote hace fallar la preparación antes de consumir memoria sin límite.

Cuando existen revisiones exactas de ambas etapas, una adjudicación puede conservar sus dos evaluaciones independientes. Los campos actuales no se mezclan con la observación histórica revisada. Las pruebas sintéticas verifican que `prepare_rows` y la inferencia reciben exactamente los mismos valores y que el importe adjudicado nunca entra al modelo de convocatoria.

Si todas las operaciones se abstienen, el candidato no sustituye el corte publicado y se pausa la actualización para revisión. Aún no hay observaciones reales revisadas ni modelos reales aprobados; la equivalencia documentada con datos de prueba no acredita calidad temporal de un corpus real.

## Uso en entrenamiento

Cada fila del conjunto añade `feature_evidence_id`; el resto debe coincidir exactamente con la observación registrada. Cambiar un valor, fecha, identidad o metadato invalida esa correspondencia. El trabajo administrativo exporta el registro de revisiones desde la base y congela su hash junto a datos y casos. El proceso aislado vuelve a comprobar los archivos físicos y reporta exclusiones.

El informe y el modelo enlazan por hash el recibo de evidencia: política, registro, número de filas y conjunto preparado. La misma aprobación se comprueba al activar y al iniciar la programación local. Un conjunto sin revisiones válidas produce exclusiones y bloqueo de entrenamiento, no modelos aprobados.

## Alcance de la comprobación

El software comprueba integridad de bytes, identidad, correspondencia exacta y coherencia de fechas declaradas. La autenticidad material, el significado del documento, las fechas que demuestra y la corrección de extracciones o cálculos dependen de la revisión humana documentada. Un hash no prueba por sí solo ninguno de esos hechos.

Las pruebas en `Backend/tests/test_risk_feature_evidence.py` contienen documentos ficticios marcados como tales y solo verifican ingeniería. No se incorporan al inventario judicial ni al registro operativo. Todavía no hay observaciones judiciales reales habilitadas para entrenar.
