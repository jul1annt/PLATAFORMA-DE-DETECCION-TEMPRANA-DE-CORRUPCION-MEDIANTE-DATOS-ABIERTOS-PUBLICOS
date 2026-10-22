# Revisión 8: efecto documental de la firmeza

Se preservaron nueve fuentes oficiales adicionales mediante el catálogo [de firmeza](fuentes_firmeza_judicial_20261018.json). La adquisición terminó sin errores; sus originales y recibos con hashes están en el directorio privado del corpus. La búsqueda sigue siendo acotada y no acredita ausencia de otras decisiones.

## Hallazgos revisados

- El anuncio del sentido del fallo de 25/04/2025, página física 96, anuncia una sentencia posterior. La ausencia de recursos contra ese anuncio no demuestra firmeza de SEP060-2025.
- La constancia del expediente 00904 de 26/03/2026, páginas 1–2, abre el término de apelación de SEP042-2026. La fecha prevista de vencimiento no acredita que no se interpusiera recurso ni que se resolviera. La decisión referida combina condenas y absoluciones; los contratos absueltos no pueden convertirse en positivos.
- Un enlace del índice con texto relativo a 00904 remite a un documento del expediente 33663. Su página 1 corresponde a un auto procesal de otra persona. La identidad se verifica en el documento, sin deducirla del texto del enlace.

Estas cuatro páginas fueron revisadas visualmente; los demás avisos se examinaron mediante extracción de texto. Ninguno se admitió como prueba de firmeza de una condena vinculada a operaciones SECOP. Los originales consultados están en el catálogo; no se trasladan decisiones de un expediente a otro por coincidencias de nombre.

## Cambio de admisión

La política `reviewed-finality-effect-v1` exige revisión expresa de `finality.reviewed=true`, `finality.effect=FIRMEZA_CONFIRMADA` y un localizador documental no vacío. Se conservan los requisitos previos de clase documental, archivo físico, hash y vínculo a la sentencia. Un título que diga «ejecutoria», un plazo vencido o la firmeza de un auto no sustituyen esos requisitos.

El [inventario revisión 8](INVENTARIO_CASOS_REVISION8_20261018.json) contiene diez candidatos y **cero utilizables**. La nueva pista 00904 se registra únicamente para localizar la sentencia original, las actuaciones posteriores y sus operaciones exactas. No contiene etiquetas ni adjudicaciones inferidas.

La suite completa del backend aprobó **591 pruebas**; diez incorporan anuncios de fallo, efectos documentales inadecuados y revisión de firmeza ausente. Las 27 pruebas de herramientas del corpus corresponden a la ejecución previamente documentada. No se entrenaron ni activaron modelos; la nueva publicación sigue pendiente.

## Seguimiento posterior al inventario

Se localizó y preservó el [original de SEP042-2026](https://archivodigitalapi.cortesuprema.gov.co/share/2026/3/Sentencias/00904%20SEP04120260325.pdf), 438 páginas, SHA-256 `2c4dd2a4856a135b0acac10f8b53b86a055415a28916ef17ad5331c1c48e627b`. Las páginas físicas 1 y 438 se revisaron visualmente. El nombre del archivo dice SEP041, pero la portada dice SEP042-2026, expediente 00904, 25/03/2026. La página 438 permite apelación. Este hallazgo resuelve la localización del original, sin demostrar firmeza ni correspondencias SECOP. El inventario revisión 8 conserva el estado anterior a esta adquisición; no se sobrescribe.

El [catálogo de seguimiento](fuentes_seguimiento_00904_20261018.json) conserva la URL; el recibo privado `runs/20261019T044522753908Z.json` registra una adquisición correcta. La extracción de texto de las 438 páginas se preservó por hash; el primer intento de imprimir su resumen falló por la codificación de consola y se repitió correctamente con escapes Unicode, sin repetir la descarga. Falta revisar los hechos y la parte resolutiva completos y localizar las actuaciones posteriores.
