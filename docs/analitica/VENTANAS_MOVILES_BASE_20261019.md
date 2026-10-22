# Base de evidencia para ventanas móviles

Estado inicial documentado: implementación local de referencia, validada con casos sintéticos. No está conectada a la consulta ciudadana ni a la activación de modelos. El avance posterior detalla el contraste empírico disponible y sus límites.

Avance posterior: el [piloto SECOP local](VENTANAS_MOVILES_PILOTO_SECOP_20261019.md) comprobó la disponibilidad de contexto para las 1.698 filas del grupo IQR y adquirió 13 historias de pares admisibles del universo normalizado local. Sus límites de cobertura, 88 pruebas enfocadas y resultados están documentados; la equivalencia SQL y la cobertura fuera de ese universo permanecen pendientes.

## Responsabilidades

`Backend/modules/motor_riesgo/rolling_evidence.py` calcula evidencia con biblioteca estándar, sin SQL, credenciales ni dependencias de entrenamiento. `Backend/scripts/risk_rolling_context.py` lee y escribe JSON local; registra hashes de entrada y siete archivos de implementación. La cobertura existente transforma los conteos conocidos en señales y limita a un punto la familia concentración/reiteración.

Esta herramienta complementa la evaluación de IQR del corte. No traslada los puntajes de proveedor a sus contratos. El contexto SQL anterior de `history.py` y el comparador simplificado `rules.rolling_context` continúan separados; todavía no se ha demostrado su equivalencia con esta referencia estricta. No se ha sustituido el procesador operativo.

## Contrato de entrada

- `scope.temporal_scope`: `current_cut_descriptive_not_stage_prediction`.
- `scope.raw_rows`: número exacto de filas suministradas, entre cero y 20.000.
- `scope.complete_pair_history`: booleano; debe respaldarse con una extracción completa del par, de todas las modalidades y categorías, sin seleccionar por puntaje.
- `scope.start` y `scope.end`: instantes con zona horaria. La cobertura debe alcanzar 30 días para reiteración y 90 para directas.
- `target`: `source_id`, `process_id`, `award_id`, `buyer_key`, `supplier_key`, `category`, `award_at`, `identity_verified`.
- Cada fila de `rows`: los mismos datos de identidad y fecha, más `direct`, `method_semantics_verified`, `method`, `amount`, `currency` y `justification` cuando estén disponibles.

Las claves de entidad/proveedor deben proceder de la normalización comprobada de SECOP; los nombres no sirven para unir registros. `identity_verified` debe comprobar la unidad fuente/proceso/adjudicación y sus posibles alias en el universo, no solo dentro del archivo. `method_semantics_verified` requiere revisar el significado del campo; una coincidencia de texto con «directa» no basta. Estos booleanos son precondiciones del llamador, no pruebas independientes obtenidas por el módulo.

Los importes y monedas deben ser datos de adjudicación. La fecha requerida es la de adjudicación; no se sustituye por publicación. La herramienta rechaza fechas sin zona, pares distintos, marcos incompatibles e identidades objetivo incompletas. Un archivo descriptivo nunca se admite como reconstrucción temporal de entrenamiento.

## Fórmulas y límites

Para el objetivo con fecha `t`, se excluye todo su proceso, incluidas sus demás adjudicaciones:

| Indicador | Ventana inclusiva | Unidad de frecuencia | Condición |
|---|---|---|---|
| Reiteración | `[t − 30 días, t]` | Fuente y proceso distintos | Mismo par y categoría |
| Directas | `[t − 90 días, t]` | Fuente y proceso distintos | Mismo par y modalidad directa verificada |

Dos fuentes con un mismo texto de proceso siguen siendo identidades distintas. Las múltiples adjudicaciones se conservan en la evidencia, pero cuentan una sola vez por proceso en la frecuencia. Las copias exactas de una adjudicación no se suman; versiones contradictorias requieren conciliación y dejan el conteo afectado desconocido.

Se conserva el importe observado por moneda, sin conversiones ni sumas entre monedas. La falta de importe no borra una frecuencia verificable; sí impide declarar completo el importe agregado. La ausencia de categoría afecta a reiteración; una modalidad no verificada afecta a directas. Una identidad o fecha inválida dentro del contexto deja desconocidas las ventanas que podría afectar.

Los eventos posteriores a `t` y los anteriores a 90 días no se cuentan. Un marco vacío puede acreditar cero únicamente si la extracción completa está comprobada y cubre la ventana. Con historia parcial, `count=null`; `observed_distinct_processes` conserva solo lo efectivamente identificado. No se convierte ese número parcial en riesgo bajo.

Los umbrales de desarrollo continúan en tres procesos directos o dos reiteraciones; la familia aporta como máximo un punto. Son decisiones operativas pendientes de evaluación, no límites legales ni coeficientes calibrados. Esta extracción del par no incluye el denominador de la entidad: no mide cuota de mercado ni concentración económica completa. Ninguna señal acredita corrupción o fraccionamiento.

## Ejecución y validación

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_rolling_context.py --input historial-par.json --output diagnostico-par-nuevo.json
```

Entrada máxima de 16 MiB; salida exclusiva, sin sobrescritura. No accede a bases de datos, no cambia dependencias, no entrena ni publica. En esta entrega pasaron **86 pruebas enfocadas** de ventanas, IQR y cobertura. Incluyen 30 casos del nuevo módulo y CLI; no equivalen a una ejecución completa del backend. El recibo `VALIDACION_VENTANAS_MOVILES_BASE_20261019.json` conserva el identificador y los hashes de esta ejecución.

## Trabajo pendiente

1. Adquirir una historia completa de un par SECOP con fechas de adjudicación, cobertura de fuente y comprobación global de identidad; conservar consulta, corte y hashes.
2. Revisar el diccionario de modalidades y procedencia de sus justificaciones. No inferir competencia por el nombre de la modalidad.
3. Comparar evidencia y consultas SQL en una copia aislada, incluyendo identidades ambiguas y datos faltantes; corregir discrepancias antes de integrarlas.
4. Combinar con IQR únicamente cuando coincidan identidad, objetivo, corte y alcance temporal. Los 1.698 diagnósticos anteriores siguen sin riesgo completo.
5. Repetir sensibilidad sobre familias corregidas y ampliar grupos. El entrenamiento y la publicación siguen condicionados a evidencia y validación independientes.
