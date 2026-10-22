# Revisión 9: recursos acreditados y nuevas correspondencias

El [inventario vigente](INVENTARIO_CASOS_REVISION9_20261018.json) contiene **once candidatos y cero aptos**. Se preservan las revisiones anteriores. El [seguimiento estructurado](SEGUIMIENTO_RECURSOS_Y_VINCULOS_20261018.json) conserva URLs, hashes, páginas y límites de cada hallazgo.

La [cobertura temporal](COBERTURA_CORPUS_REV9_20261018.json) separa años contractuales declarados de candidatos y fechas de etiquetas admitidas. Estas últimas siguen vacías: no existe todavía cobertura temporal apta para entrenamiento. Los conteos por año no representan operaciones ni expedientes positivos independientes.

## Recursos contra dos sentencias investigadas

Se adquirieron el índice de traslados, cuatro avisos procesales y una sentencia de casación con su comunicado oficial: siete fuentes, sin errores de adquisición. Se revisó visualmente la página 1 de cada traslado.

- **00904 / SEP042-2026:** los avisos del 07/04 y 13/04/2026 acreditan apelación interpuesta y posteriormente sustentada por defensa y parte civil. No se localizó su resolución posterior. La página 436 del original, también revisada visualmente, conserva absoluciones para contratos 4 y 12 e interventorías 16 y 17. No se etiquetan las operaciones mencionadas en conjunto.
- **00641 / SEP060-2025:** los avisos del 16/05 y 30/05/2025 acreditan recursos de defensa y Fiscalía contra esa sentencia. No se confunde este expediente con otras causas contra la misma persona. Los avisos demuestran esas actuaciones en sus fechas; no prueban por sí solos el estado procesal actual.

## SECOP Integrado conserva otra referencia histórica

Se verificaron los metadatos de `rpmr-utcd`: procedencia oficial, SECOP Integrado. Las consultas fueron acotadas a 31 filas; ninguna consulta correcta alcanzó ese límite. Los cuerpos originales quedaron preservados por hash.

| Operación investigada | Correspondencia candidata | Límite pendiente |
| --- | --- | --- |
| Arauca, 362 del 10/12/2012 | Constancia `12-9-357532`, proceso `SU-06-09-2012`, Consorcio R& S 2012, misma fecha, entidad y mobiliario escolar | El literal 362 y un ID de adjudicación no aparecen en esta respuesta. Falta conciliación documental completa |
| Arauca, 497 del 09/10/2013 | Constancia `13-9-372325`, proceso `SU-06-14-2013`, Consorcio Educando Arauca | El importe de SECOP Integrado difiere del importe de adjudicación del archivo OCDS. No se igualan automáticamente |
| Ruta del Sol, SEA-LP-001-2009 | Constancia `09-1-41316`, cuatro filas con dos contratistas | Identificar el sector y adjudicación; no extender la condena a todos los contratos del proceso |

La nueva correspondencia del 362/2012 no contradice la lectura anterior del archivo anual: aquella búsqueda acotada no lo había encontrado y nunca acreditó inexistencia. El 362 del 31/07/2013 conserva su exclusión por ser otra operación.

En SECOP Integrado `numero_del_contrato` contiene, en estos resultados SECOP I, la constancia de proceso. No se trata como número literal del contrato ni como identidad de adjudicación. El campo se preserva con su nombre y valor originales. Estas filas actuales incluyen ejecución posterior; **no son observaciones históricas válidas para entrenamiento**.

La primera consulta con selección de columnas de sistema fue rechazada con HTTP 400; la repetición corregida obtuvo resultados. Se preservó el registro del fallo. Otro conjunto enlazado por diccionarios tenía procedencia comunitaria y no se admitió como fuente oficial; un conjunto adicional devolvió 403. Los enlaces de detalle de contratos.gov.co no pudieron consultarse mediante la herramienta web.

## Nueva sentencia de casación

SP1919-2025, expediente 58953, de 24/09/2025, se conservó en original: 61 páginas, SHA-256 `454526891e3105802d189f70db246450beacad60df2098b92ab41ae9b58b1323`. Se revisaron visualmente las páginas 2, 3 y 60. La parte resolutiva no casa la sentencia de 28/09/2020 y señala que no proceden recursos contra esa providencia. Sus referencias distinguen sector 2, licitación de 2009 y contrato 001 de 14/01/2010.

El nuevo registro sigue siendo candidato: falta obtener la condena de instancia original, completar la revisión de hechos y clasificación, vincular la adjudicación exacta, fijar disponibilidad de la etiqueta y cronología inicial de investigación y reconstruir variables fechadas de ambas etapas. No se introduce una fecha de firmeza deducida del comunicado ni se utiliza la imputación como inicio cierto de toda investigación.

## Alcance de esta revisión

Se actualizaron únicamente documentos, el registro de investigación y copias documentales privadas. El código del motor no cambió; la validación de **591 pruebas** de la revisión anterior conserva ese alcance. Se ejecutó de nuevo el inventario sobre el registro actual, que comprobó elegibilidad y archivos presentes. No se repitieron cargas, ensayos de volumen ni migraciones ya comprobadas. No hubo entrenamiento, cambios a la base publicada o activación.
