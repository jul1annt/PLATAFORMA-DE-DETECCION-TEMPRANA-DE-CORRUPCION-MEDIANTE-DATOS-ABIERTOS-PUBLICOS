# Revisión 12 — correspondencias históricas SECOP

## Resultado

Se revisaron por flujo **2.131.839 líneas** de los archivos oficiales SECOP I de 2012, 2013 y 2015. Las tres ejecuciones terminaron con tamaño, CRC, respuesta HTTP 206 y generación comprobados. Solo se guardaron quince líneas candidatas y muestras acotadas de esquema; los ZIP y miembros completos no se escribieron en disco.

El [informe verificable](CORRESPONDENCIAS_HISTORICAS_GUAINIA_PUTUMAYO_20261019.json) conserva consultas, hashes, posiciones, identificadores publicados y discrepancias. El [inventario 12](INVENTARIO_CASOS_REVISION12_20261019.json) sigue en **14 candidatos y cero aptos**; la [cobertura](COBERTURA_CORPUS_REV12_20261019.json) mantiene separadas las fechas de candidatos y las de etiquetas admitidas.

## Correspondencias candidatas

| Contrato judicial | Constancia publicada | Adjudicación en archivo | Alcance |
| --- | --- | --- | --- |
| Guainía 068/2013 | 12-1-84082 | 7769884 | Pueblo Nuevo / Unión Temporal CAM; resolución 0175 recuperada en el detalle oficial |
| Guainía 069/2013 | 12-1-84081 | 7455850 | Candidata por referencia; revisión judicial por operación pendiente |
| Guainía 070/2013 | 12-1-83953 | 7769974 | El archivo escribe el número como `70`; no se cambia el identificador publicado |
| Guainía 079/2013 | 12-15-1269067 | 3319750 | Candidata por referencia; no se propaga etiqueta de las obras a la interventoría |
| Guainía 204/2013 | 13-11-1538012 | 1550735 | Mapiripana / Consorcio Pisga; revisión judicial por operación pendiente |
| Guainía 205/2013 | 13-11-1537995 | 1560801 | La Unión / Unión Temporal 2013 La Unión; revisión judicial por operación pendiente |
| Putumayo 1226/2015 | 15-11-4399251 | 4225659 | Coinciden entidad, proveedor, objeto y referencias de contrato y resolución; discrepancias conservadas |

Ocho coincidencias numéricas adicionales pertenecen a convocatorias distintas o a otro año contractual. No se vincularon al caso. Los seis contratos de Guainía permanecen en un único grupo relacionado; no fabrican seis expedientes independientes. Los IDs de archivo no se asignaron a filas del corte local ni al legado.

## Contraste de documentos originales

En el [detalle oficial de Putumayo](https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia=15-11-4399251) se descargaron normalmente el contrato y el acto de adjudicación. El contrato escaneado muestra **28/12/2015** en portada y página de firmas, frente a **28/01/2016** en el campo estructurado y el archivo. Se preservan ambas versiones. La resolución 1647 del **21/12/2015**, página física 3, acredita **86.020.000 COP**, diferente de los 86.000.000 registrados desde el resumen judicial. No se sobrescribe la procedencia de ninguna cifra.

La resolución de Putumayo fue publicada, según el índice consultado, el **22/12/2015 a las 17:28**, y el contrato el **15/01/2016 a las 16:10**. La fecha del documento no demuestra disponibilidad anterior a su publicación. Ninguno se convirtió automáticamente en variable disponible al adjudicar el 21/12.

En el [detalle oficial de Guainía 068](https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia=12-1-84082) se recuperó la resolución **0175 del 15/02/2013**, que identifica el proceso completo y adjudica a Unión Temporal CAM por **1.364.873.500 COP**. La página 4 diferencia este importe del presupuesto de **1.364.875.997 COP**. El cronograma y el archivo conservaron **20/12/2012** como fecha de adjudicación, mientras el índice muestra publicación de la resolución el **21/02/2013 a las 11:15**. No se usa una fecha prevista como actuación efectiva ni como disponibilidad pública.

Los tres PDF adquiridos se conservaron por SHA-256. La revisión visual fue parcial: contrato Putumayo páginas 1 y 12; resolución Putumayo página 3; resolución Guainía páginas 4 y 5. El auto de preacuerdo y las sentencias siguen teniendo sus propios alcances de revisión. No se certifica aquí integridad jurídica, firmeza o revisión de todas las páginas.

## Herramienta de búsqueda y validación

`corpus_tools.scan_history` admite perfiles explícitos `gobernacion-arauca`, `gobernacion-guainia` y `gobernacion-putumayo`; el valor predeterminado conserva Arauca. La entidad se comprueba dentro de `buyer`, después de decodificar el JSON, y los números se buscan en campos contractuales y en el título del proceso. Las coincidencias en el título siguen siendo pistas, nunca identidades contractuales confirmadas.

El archivo 2015 inspeccionado contiene un miembro de 3.361.249.396 bytes, mayor que el límite anterior de 2 GiB. Se amplió el límite a **4 GiB**, manteniendo lectura comprimida por bloques de 256 KiB, descompresión por bloques de 1 MiB, límite de línea de 2 MiB y retención de hasta 50 candidatos. Se rechazan perfiles desconocidos antes de consumir red o flujo, miembros cifrados, nombres o compresión distintos y tamaños fuera del límite. Se conserva la comprobación de generación al terminar.

Pasaron **37 pruebas** de las herramientas documentales. Incluyen perfiles cruzados, acentos y Unicode escapado, entidades mencionadas solo en el objeto, teléfonos, límites numéricos, CRC y límites del miembro. El primer intento de 35 pruebas tuvo cuatro errores por permisos de temporales de Windows; la repetición autorizada pasó y la versión final pasó las 37. El informe registra el log y los hashes. No se repitió la suite backend inalterada de 656 pruebas ni los ensayos de volumen anteriores.

## Pendientes

Faltan firmeza documentada y fechada, revisión completa del alcance condenado, correspondencia con observaciones de entrenamiento e información disponible en cada etapa anterior al corte de investigación. Los archivos anuales incorporan modificaciones posteriores; su `release.date` no los convierte en fotografías históricas completas. No se crearon operaciones de entrenamiento, etiquetas ni observaciones por etapa. No hubo acceso a las bases ni cambios de publicación.
