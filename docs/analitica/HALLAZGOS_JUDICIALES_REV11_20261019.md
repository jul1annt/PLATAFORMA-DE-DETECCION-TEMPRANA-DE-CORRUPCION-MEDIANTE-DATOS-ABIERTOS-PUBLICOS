# Revisión judicial 11 — 19/10/2026

El [inventario](INVENTARIO_CASOS_REVISION11_20261019.json) reúne **14 registros candidatos y cero casos aptos para entrenamiento**. Tres tienen conducta clasificada como corrupción, uno como fraude contractual y diez siguen por clasificar. Esa clasificación no acredita firmeza, identidad SECOP ni suficiencia. No se creó ninguna etiqueta de entrenamiento.

## Documentos incorporados

| Expediente | Evidencia revisada | Resultado y exclusión pendiente |
| --- | --- | --- |
| Guainía, SEP079-2023 / 00059 | [Sentencia original](https://cortesuprema.gov.co/corte/wp-content/uploads/2023/08/SEP079-2023.pdf), páginas físicas 1, 5, 192, 193 y 195 | La parte resolutiva incluye interés indebido y cohecho. Se conserva un solo grupo relacionado para las seis actuaciones acumuladas. La sentencia permite apelación; falta firmeza, vínculo por operación y evidencia histórica. |
| Putumayo, SP1731-2025 / 60747 | [Apelación](https://archivodigitalapi.cortesuprema.gov.co/share/2025/8/Documentos/SP1731-2025%2860747%29.pdf), páginas 1, 4, 5 y 157; [primera instancia SEP115-2021](https://cortesuprema.gov.co/corte/wp-content/uploads/2021/09/SEP-00115-2021-2.pdf), páginas 1, 237 y 239 | La apelación confirma la condena e indica que no procede recurso. No se transforma esa frase en una fecha de ejecutoria o disponibilidad de etiqueta. El contrato referido es 1226/2015. Faltan revisión completa, identidad y variables por etapa. |
| Hospital de Santander de Quilichao, SP1281-2024 / 57851 | [Sentencia original](https://cortesuprema.gov.co/corte/wp-content/uploads/relatorias/pe/b1jun2024/SP1281-2024%2857851%29.pdf), páginas 1 y 151 | La parte resolutiva modifica la calificación a estafa agravada y declara prescripción de la conducta contractual indicada. Se conserva separado como fraude contractual, excluido del objetivo positivo de corrupción. Tampoco constituye un negativo confirmado. |

La revisión fue parcial: extraer texto o contar páginas no equivale a revisar íntegramente una decisión. Los hashes y recibos de adquisición figuran en [el registro de esta revisión](REVISION_CORPUS_20261019_REV11.json). Los originales permanecen en el almacén local inmutable y en el directorio de evidencias.

## Corrección de una asociación documental

Un resultado de una página agregada de noticias llevó inicialmente a SEP119-2021. La inspección de portada y parte resolutiva mostró que corresponde a Luis Alfredo Ramos, no al procesado del expediente Putumayo. Se conservó el cuerpo adquirido y su motivo de descarte; no se vinculó al candidato ni se contó como expediente adicional. Después se recuperó la sentencia correcta SEP115-2021.

## Cobertura y búsquedas

La [cobertura corregida](COBERTURA_CORPUS_REV11_20261019.json) considera tanto `procurement_year` como `procurement_years`. La revisión anterior omitía años guardados únicamente en el campo singular. Los conteos describen registros candidatos con años declarados, no operaciones ni grupos positivos independientes. La cobertura temporal de etiquetas admitidas continúa vacía.

Dos búsquedas SECOP por entidad, proveedor u objeto agotaron el plazo: se registraron como fallidas. Otra consulta exacta por fecha e importe devolvió cero filas. Ninguna de estas respuestas demuestra ausencia de contratos ni autoriza asignar una identidad.

## Referencias posteriores al cierre del inventario 11

Se revisó además la página física 150 de SEP115-2021: identifica el proceso `SPCD-SAMC-003-2015`, resolución 1647 del 21/12/2015 y contrato 1226 del 28/12/2015. La consulta exacta de ese proceso en Integrado `rpmr-utcd` devolvió cero filas. El recibo local `secop-research/putumayo-exact-process-20261019.json` conserva consulta y cuerpo por hash. La nota al pie menciona una investigación relacionada y un informe de septiembre de 2018: la apertura de octubre de 2018 no se acepta automáticamente como primera investigación.

Se adquirió el [auto de preacuerdo de Guainía](https://cortesuprema.gov.co/corte/wp-content/uploads/2023/05/00059-PREACUERDO-FIRMA-DIGITAL.pdf), SHA-256 `b95aefe7c8d7822f04ef3dd58b48ef373824f556471b0c626b2532488ad2a348`. La página física 15 identifica resolución 0175 del 15/02/2013, proceso `LP-SPD-OP-015 de 2012`, contrato 068 del 28/02/2013 y Unión Temporal CAM. Es una pista documental, no otra sentencia ni un caso independiente. Estas comprobaciones posteriores se conservan aquí sin reescribir el inventario 11 ya emitido.

## Estado del plan

Continúan pendientes la firmeza documentada y fechada, la correspondencia exacta de las operaciones, la evidencia disponible en cada etapa y una cantidad suficiente de expedientes independientes. No se entrenaron ni aprobaron modelos reales, no se accedió a la base durante esta revisión y no se cambió la publicación. El corte publicado del 01/10/2026 se conserva.
