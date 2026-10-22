# Revisión 13 — evidencia declarativa de firmeza

## Hallazgo en la relatoría oficial

La consulta por número de providencia en el [Sistema de Consulta de Jurisprudencia de la Corte](https://consultajurisprudencial.ramajudicial.gov.co/WebRelatoria/csj/index.xhtml) devolvió un resultado: **AEP012-2024**, radicado **00059**, ID **867595**, auto interlocutorio del **05/02/2024**, Sala Especial de Primera Instancia, ponente Ariel Augusto Torres Rojas.

Su apartado oficial de consideraciones, sección de competencia, identifica la sentencia **SEP079-2023 del 20/06/2023**, a los dos exgobernadores de Guainía y afirma que está ejecutoriada. Esto aporta una confirmación expresa de firmeza en una fuente institucional posterior. No se deduce únicamente de que exista un incidente de reparación.

El menú de descarga PDF devolvió `format.html`, cuyo contenido indica que el documento no está disponible en medio magnético. Ese cuerpo se conserva por hash como aviso de indisponibilidad; **no es el auto original ni una constancia de ejecutoria**. El buscador de texto completo, consultado por el mismo número en su sección Penal, no devolvió resultados; no se extiende ese resultado al universo completo de Primera Instancia.

Una transcripción secundaria permitió localizar la actuación y menciona una ejecutoria en la fecha de emisión de la sentencia. Ese dato no se incorpora como `final_at`: todavía debe contrastarse con el documento judicial completo. La fecha del auto posterior tampoco sustituye la fecha de ejecutoria ni demuestra cuándo se hizo pública la etiqueta.

## Ajuste del registro judicial

La política `reviewed-finality-effect-v2` incorpora `PROVIDENCIA_ACREDITA_FIRMEZA` como alternativa a una constancia de ejecutoria o la resolución del último recurso. Una providencia posterior puede declarar la firmeza de una condena; restringir la evidencia únicamente a esos dos tipos descartaba una vía documental pertinente.

La nueva categoría exige todos los controles existentes: archivo local, hash íntegro, URL institucional, vínculo al hash de la condena específica, revisión expresa del efecto y localizador. Además exige:

- `declared_final_at`: fecha y zona horaria documentadas, coincidentes con `final_at`.
- `declaration_date_locator`: ubicación de la declaración de esa fecha en el documento.

Una mención de firmeza sin fecha, un extracto sin el original o un auto que solo está ejecutoriado por sí mismo no habilitan el caso. La nueva categoría tampoco evita los requisitos de operaciones exactas, conducta acreditada, evidencia anterior a investigación y disponibilidad de la etiqueta.

## Estado

El inventario continúa con **14 registros y cero aptos para entrenamiento**. Guainía conserva la confirmación institucional como investigación documental; no se creó su campo `finality` ni se fijó una fecha inferida. Faltan el original completo, la fecha verificable y el resto de requisitos de admisión.

Pasaron **674 pruebas del backend** (91 en la ejecución focalizada inicial), sin fallos, errores ni omisiones. La validación del software y las lecturas de las bases se documentan en [el informe de validación](VALIDACION_FIRMEZA_DECLARADA_20261019.json). Se conservaron los esquemas publicados y de pruebas, sin ejecutar migraciones ni volver a comprobar HTTP. Las pruebas sintéticas no acreditan capacidad predictiva real. El corte publicado del 01/10/2026 y la condición de no activar modelos sin evaluación se mantienen.
