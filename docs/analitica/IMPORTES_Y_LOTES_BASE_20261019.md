# Importes exactos y lotes reproducibles de ventanas móviles

Avance posterior: los conteos estrictos ya se [integraron al materializador de diagnóstico](INTEGRACION_SQL_VENTANAS_20261019.md), con 958 pruebas del backend correctas. Se mantiene la abstención de importes sin moneda; la integración de familias y las validaciones adicionales continúan pendientes. Este documento conserva la evidencia de la entrega monetaria y del lote desconectado.

## Política monetaria v2

La referencia móvil usa ahora `verified-pair-rolling-current-cut-v2`. Los informes anteriores de v1 se conservan; no se sobrescribieron. Los conteos, las ventanas y los pesos mantienen su definición.

Se detectó un límite en la suma anterior: un contexto Decimal de 28 dígitos podía perder centavos con importes grandes. La nueva política monetaria `positive-numeric38-2-no-rounding-v1` admite importes positivos representables en `NUMERIC(38,2)`, con hasta 36 dígitos enteros y dos decimales efectivos. Valores con fracciones de centavo, no finitos, booleanos, fuera de rango o representaciones superiores a 128 caracteres quedan sin importe evaluable; no se redondean para admitirlos.

La suma usa 64 dígitos de precisión. El máximo de 20.000 adjudicaciones por marco requiere menos de 44 dígitos para sumar esos importes con sus centavos, por lo que la capacidad no depende de la precisión Decimal del llamador. Por ejemplo, `123456789012345678901234567890123456.78 + 0.01` conserva el resultado terminado en `.79`.

Los totales se expresan con dos decimales y se separan por moneda. Se comprueba únicamente la sintaxis de un código de tres letras ASCII mayúsculas declarado por la entrada: no se valida aquí un catálogo de monedas ni su denominación documental. La falta de importe o moneda no elimina una frecuencia comprobada; el subtotal observado puede conservarse, pero `amounts_complete=false` impide presentarlo como total completo. La cobertura temporal o de identidad incompleta también impide declarar completo el importe.

## Comparación SQL ampliada

El comparador ahora contrasta sumas por moneda, integridad del total y número de adjudicaciones sin importe/moneda válidos, además de conteos, exclusiones y motivos de calidad. PostgreSQL agrega valores `numeric` por separado de la suma Decimal. El análisis y admisión de cada importe se comparten con el dominio: **la concordancia SQL no constituye una segunda validación independiente del formato de origen**. Se prueban explícitamente los límites y los centavos con resultados esperados literales.

Las 13 entradas SECOP guardadas volvieron a coincidir con SQL en la base aislada OID 82244, mediante una transacción de solo lectura. Sus ventanas reales no contienen procesos previos; esta comprobación no prueba la existencia de importes denominados correctamente en los documentos. Los casos sintéticos con varias monedas, copias e importes grandes cubren las rutas de suma que el piloto real no ejercita.

## Lote local reanudable

`Backend/scripts/risk_rolling_batch.py` procesa en serie un manifiesto de entradas locales con hashes. No usa SQL, API, bibliotecas de entrenamiento ni consultas de red.

```json
{
  "version": "rolling-batch-input-v1",
  "inputs": [
    {"path": "historial-par.json", "sha256": "HASH_SHA256_DE_64_CARACTERES"}
  ]
}
```

Las rutas deben permanecer dentro del directorio del manifiesto. Se rechazan rutas absolutas, escapes, archivos repetidos y hashes incompatibles. Los límites son 1.000 entradas, 16 MiB por entrada y 256 MiB por lote. El código trabaja con una entrada a la vez.

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_rolling_batch.py --manifest Backend/.codex-analytics-postgres/rolling-batch-money-v2-input-20261019.json --output-directory Backend/.codex-analytics-postgres/rolling-batch-money-v2-20261019
```

El directorio queda vinculado al hash del manifiesto, versión de Python, política y hashes del código. No se reutiliza con datos o implementación diferentes. Un bloqueo del sistema operativo impide dos trabajadores simultáneos y se libera si termina el proceso. Cada salida se escribe en un archivo temporal, se vacía y sincroniza y finalmente se reemplaza de forma atómica; una salida existente solo se admite si es idéntica.

Al reanudar, se recalculan los diagnósticos para comprobar igualdad y se conservan los archivos ya completos. No se vuelve a extraer información de SECOP. Una interrupción deja los resultados terminados disponibles para esa verificación; no genera un recibo de lote completo. Solo tras comprobar todas las entradas y el código se escribe `complete.json`. Este recibo significa **diagnóstico desconectado completo**, no riesgo completo ni publicación ciudadana; sus resultados y hashes deben verificarse al consumirlo.

El lote guarda también una copia de nueve archivos de código necesarios para reproducirlo. Esa copia se ejecutó con Python `-I -S`, sin paquetes externos, desde un directorio distinto. La ejecución reprodujo el manifiesto completo, byte por byte. Las entradas siguen siendo privadas y se necesitan para reproducir el cálculo.

## Evidencia de esta entrega

| Comprobación | Resultado |
|---|---:|
| Pruebas enfocadas | 147 correctas, cero fallos o saltos |
| Pruebas del lote | 11 |
| Pruebas SQL | 39, incluyendo 100 marcos mixtos reproducibles |
| Pruebas de referencia móvil | 41 |
| Pruebas de IQR y cobertura | 18 + 38 |
| Archivos reales del lote | 13 |
| Salidas idénticas conservadas en segunda ejecución | 13 |
| Consultas nuevas para ejecutar o repetir el lote | 0 |
| Puntajes de riesgo completos | 0 |

La primera ejecución del lote tardó aproximadamente 1,13 segundos; la verificación con conservación de salidas, 0,44; la reproducción desde la copia congelada, 1,32. Son tiempos de esas 13 entradas pequeñas, no una medición del universo completo. Las pruebas también comprobaron interrupción, salida alterada, entrada modificada, cambio de código, bloqueo simultáneo y liberación al terminar un proceso.

El [recibo con hashes y resultados](VALIDACION_IMPORTES_Y_LOTES_VENTANAS_20261019.json) enlaza la batería, el lote y la comparación real en SQL. No equivale a una nueva batería completa del backend. El lote y los ensayos SQL no accedieron a la base original ni modificaron datos operativos.

## Integración pendiente

El materializador anterior `history.py` todavía no está reemplazado ni declarado equivalente. El siguiente paso es trasladar estas reglas a su procesamiento por lotes y comprobarlas con datos e identidades ambiguas en la copia aislada. También falta combinar IQR y ventanas por identidad, corte y alcance compatibles, y verificar los campos de competencia antes de obtener puntajes completos.

La referencia de un punto por familia y los coeficientes históricos 1 / 1,5 / 2 permanecen intactos. Esta mejora asegura cálculo y trazabilidad; no calibra los pesos ni convierte las señales en probabilidades de corrupción. No hubo entrenamiento, activación, publicación nueva ni contacto con terceros.
