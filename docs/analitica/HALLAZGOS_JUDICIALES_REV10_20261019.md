# Revisión 10: clasificación y alcance del caso Ruta del Sol

## Inventario vigente

La [revisión 10](INVENTARIO_CASOS_REVISION10_20261019.json) registra **once candidatos, uno con conducta clasificada como corrupción y cero aptos para entrenamiento**. La [cobertura](COBERTURA_CORPUS_REV10_20261019.json) mantiene vacía la cobertura de etiquetas admitidas. Clasificar un delito documentado no sustituye comprobar firmeza, disponibilidad de la etiqueta, identidad SECOP y evidencia por etapa.

Se incorporó al registro candidato la sentencia condenatoria de primera instancia, con hash y archivo físico, y se añadió la apelación como documento relacionado. Los objetos completos adquiridos y el registro anterior, identificado por su hash, permanecen preservados. Los informes previos corresponden a sus respectivas revisiones.

## Conducta y operación judicial documentadas

La apelación de 28/09/2020 identifica en las páginas físicas 42 y 52–53 las conductas de cohecho por dar u ofrecer e interés indebido en la celebración de contratos. La página 60 confirma la condena con modificación de penas. Se revisó el texto de las páginas 3–5 y 41–53; además se comprobaron visualmente las páginas 43, 52 y 53, complementando las páginas 1, 60 y 62 ya revisadas. No se afirma revisión integral de las 62 páginas ni del escaneo de primera instancia.

La página física 43, dentro de la valoración probatoria de la Sala, identifica el **sector 2**, la resolución **641 del 15/12/2009** y el contrato **001 del 14/01/2010**, dentro de SEA-LP-001-2009. Se registraron como referencia jurídica, separados de `operations`, que continúa vacío. La referencia no crea un ID de adjudicación ni resuelve las cuatro filas actuales del proceso.

La página 46 descarta determinados testimonios de referencia como prueba de participación del acusado; la Sala desarrolla su fundamento probatorio en las páginas siguientes. La página 49 explica que no depende de declarar ficticio el contrato privado de asistencia técnica GF-001/2009. Por ello no se etiqueta ese contrato privado como otra contratación SECOP corrupta ni se trasladan conclusiones por nombres de empresas.

La página 53 cita jurisprudencia de otro expediente para explicar la categoría de interviniente. Ese precedente no se incorpora como un nuevo caso positivo de esta operación.

## Exclusiones que permanecen

El verificador del corpus confirmó que desaparecen para este candidato las carencias de sentencia condenatoria original y clasificación de conducta. Permanecen, entre otras, la ausencia de firmeza revisada vinculada a esa sentencia, fechas documentales de firmeza y disponibilidad de etiqueta, corte inicial de investigación, revisión final e identidad SECOP exacta. La imputación del 14/08/2017 no se convierte automáticamente en inicio de investigación.

La casación SP1919-2025 ya conservada será parte de la revisión de firmeza, sin inferir una fecha a partir de la publicación de noticias o del transcurso de plazos. La condena de 2019 y su apelación de 2020 no cuentan como dos expedientes independientes.

No se modificó la base publicada, el corte histórico ni las identidades del legado. No se entrenó o activó ningún modelo. Esta revisión modificó únicamente datos y documentación del corpus; las 613 pruebas del backend conservan el alcance de la validación técnica previa y no se presentan como validación de estas etiquetas.
