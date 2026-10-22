# Construcción del corpus judicial público

Inicio: 18/10/2026, por instrucción de construir el corpus sin insumos judiciales aportados por el usuario. Se conservan los nueve registros anteriores y sus exclusiones para no repetir investigaciones. No se modifica el requisito de decisiones firmes ni se crean datos de entrenamiento ficticios.

## Responsabilidades

- `Backend/corpus_tools/acquire.py`: adquisición explícita y acotada, biblioteca estándar, sin SQL ni módulos del modelo. Conserva cuerpos por SHA-256 y una bitácora acumulativa con URL, fecha de adquisición y tipo. La fecha de adquisición nunca se usa como publicación o firmeza judicial.
- `Backend/corpus_tools/index_pdf.py`: herramienta opcional de revisión documental, separada de la API, entrenamiento e inferencia. Usa `pypdf==6.10.0`; no instalar sus requisitos en esos otros entornos. Conserva página física, términos, contexto, páginas vecinas y enlaces externos pendientes de procedencia. No interpreta un término como condena.
- `docs/analitica/fuentes_corpus_judicial.json`: fuentes públicas seleccionadas a partir de enlaces observados en portales oficiales. No es un registro de positivos.
- `analytics_ml/corpus.py`: mantiene la admisión judicial existente; únicamente después de verificar documento original, firmeza, alcance exacto de la condena y operación SECOP se propone un caso al inventario.

## Ejecución desde Backend

```powershell
.\venv\Scripts\python.exe -m corpus_tools.acquire --catalog ..\docs\analitica\fuentes_corpus_judicial.json --root var\risk\judicial-discovery
```

La salida identifica el informe de adquisición. Para indexarlo, ejecutar con el intérprete independiente de revisión PDF:

```powershell
& $PythonRevisionPDF -m corpus_tools.index_pdf --root var\risk\judicial-discovery --acquisition $InformeAdquisicion --output $InformeNuevo
```

Las rutas de esos tres argumentos corresponden a archivos locales. La salida debe ser nueva: no se sobrescriben revisiones. Para la primera ejecución se utilizó el intérprete PDF incluido en el runtime de escritorio, cuya versión de `pypdf` se registró; no se instalaron dependencias en la API o en los modelos.

## Reanudación y límites

Se seleccionan como máximo 25 fuentes por lote, con respuestas de hasta 32 MiB y plazo de 25 segundos por solicitud. El recolector comprueba los destinos de redirección antes de acceder a ellos. No rastrea todos los enlaces ni usa credenciales. Reutiliza adquisiciones correctas, comprobando hash y tamaño; una copia alterada se informa como error y no se elimina ni sustituye automáticamente. `--refresh` solicita una nueva observación conservando el cuerpo anterior por su hash.

Un fallo de red o una fuente no accesible no demuestra ausencia de sentencia. Un PDF sin términos coincidentes tampoco equivale a ausencia de corrupción. Los términos solo priorizan páginas y pueden omitir documentos; las páginas vecinas deben revisarse. Las referencias de índices y sus repeticiones no se cuentan como expedientes independientes.

## Primera revisión

La adquisición inicial y su ampliación conservaron siete fuentes: un índice, un comunicado y cinco boletines de enero a mayo de 2024. Los boletines contienen 184 páginas. La indexación priorizó cinco páginas: dos son índices de contenido y tres contienen referencias sustantivas a actuaciones. Se revisaron visualmente marzo/página 16 y mayo/páginas 11–13. Son extractos informativos: no reemplazan las providencias originales.

Los enlaces de esas páginas apuntan al almacenamiento SharePoint referenciado por el Tribunal. Se preservaron cuatro URLs para revisar su procedencia y acceso, sin descargarlas automáticamente por estar fuera de la lista inicial de hosts. La primera comprobación anónima recibió cuatro redirecciones dentro del mismo tenant; otra comprobación identificó una ruta de vista OneDrive. No se usaron credenciales, no se acreditó todavía acceso a los originales y no se dedujo firmeza.

La siguiente acción es resolver esos enlaces públicos y ampliar las fuentes judiciales, priorizando hechos con correspondencia verificable en SECOP. No se presupone el año de contratación a partir del año del radicado. El inventario judicial de entrenamiento sigue separado: nueve registros anteriores, cero aptos. No se entrenaron ni activaron modelos en esta fase.

## Resolución de almacenamiento y resultado comprobado

`corpus_tools/storage.py` resolvió cuatro enlaces mediante sesiones públicas anónimas y redirecciones dentro del tenant judicial. Extrajo únicamente URLs de descarga presentes en el visor, sin fabricar rutas ni seguir autenticación. Los enlaces temporales del visor permanecen en el archivo local de investigación; el informe publica hashes y procedencia, sin exponerlos. Una repetición reutilizó los cuatro PDF comprobando integridad, sin nuevas descargas.

Los cuatro documentos suman 259 páginas: una revisión inicial distingue un auto de acumulación, un auto interlocutorio, una sentencia de prescripción por estafa y una absolución confirmada. Las páginas visualmente revisadas están registradas en el [informe de construcción](CORPUS_PUBLICO_20261018.json); no constituyen lectura integral ni acreditan firmeza. No se crearon etiquetas negativas o positivas ni se propagaron resultados a otras operaciones. Las 110 páginas priorizadas por términos en estos originales no representan 110 casos.

Para resolver el almacenamiento seleccionado:

```powershell
.\venv\Scripts\python.exe -m corpus_tools.storage --root var\risk\judicial-discovery --index $IndiceBoletines --output $InformeAlmacenamientoNuevo
```

El indexador PDF admite también ese informe de almacenamiento como entrada. Las 16 pruebas de adquisición y almacenamiento pasaron en ejecución nativa; el entorno restringido había negado el acceso a directorios temporales en una ejecución previa. La integración PDF se ejecutó sobre los cinco boletines y los cuatro originales. Estas comprobaciones no acreditan calidad predictiva ni sustituyen la suite previa de la API.

## Ampliación a fuentes históricas SECOP I

La [revisión 7](HALLAZGOS_JUDICIALES_REV7_20261018.md) encontró una correspondencia candidata en los archivos oficiales anteriores a 2018. Se mantuvieron separados el corte publicado, el legado y el corpus externo de investigación.

`corpus_tools/remote_zip.py` consulta el directorio mediante rangos HTTP sin descargar el ZIP completo; comprueba ETag, fecha de modificación, tamaño y respuesta 206 antes de consumir el cuerpo. `corpus_tools/scan_history.py` lee el miembro comprimido por flujo y verifica CRC, tamaño y generación también al finalizar. Solo conserva líneas candidatas, con hash y posición. El perfil inicial busca números explícitos en campos contractuales de Gobernación de Arauca; no es un rastreador general de todos los expedientes colombianos.

El formato observado es JSON por línea, con envoltura `Release` y codificación CP1252. La decodificación es estricta, sin sustituir caracteres. Una fecha de release no se considera disponibilidad temporal de todos los campos. Los IDs de proceso y adjudicación se preservan como aparecen; no se propagan al corte ni a contratos relacionados.

```powershell
.\venv\Scripts\python.exe -m corpus_tools.remote_zip --year 2013 --output $DirectorioNuevo
.\venv\Scripts\python.exe -m corpus_tools.scan_history --year 2013 --number 497 --number 362 --root $CandidatosLocales --output $InformeNuevo
```

La salida se conserva en archivos nuevos y los fallos no autorizan etiquetas ni publicación. Las 27 pruebas actuales incluyen rangos ignorados, generaciones distintas, CRC erróneo, fin incompleto, números dentro de teléfonos y contratos de otras entidades. Las dos lecturas históricas fueron ensayos reales completos; la suite previa de 581 pruebas de la API no se repitió en esta fase documental.

## Documentos para reconstruir etapas

La [revisión de Ruta del Sol](EVIDENCIAS_ETAPA_RUTA_DEL_SOL_20261018.md) recuperó dos documentos del portal histórico de ANI después de errores 404 en enlaces actuales. Se añadieron únicamente `www.ani.gov.co`, `ani.gov.co` y `wwwold.ani.gov.co` a los hosts del recolector, sin admitir automáticamente todos los subdominios oficiales. Las 28 pruebas documentales pasaron y el caché reutilizó ambos cuerpos sin red.

Se preservan el pliego definitivo de 2009 y una copia contractual generada en 2013. Se distinguen fechas previstas, actuaciones efectivas y disponibilidad documental. No se retrofecha la copia a la convocatoria o adjudicación ni se mezclan VPIT y presupuesto global. No se admitieron observaciones de etapa. El inventario vigente sigue siendo la [revisión 9](INVENTARIO_CASOS_REVISION9_20261018.json).

El [seguimiento del 19/10](SEGUIMIENTO_PREPLIEGO_SAMAI_20261019.md) preserva el prepliego, una adenda y la providencia oficial que localiza las copias penales en SAMAI. Se incorporaron únicamente los dos hosts seleccionados del Consejo de Estado para la providencia pública; el detalle del expediente permanece detrás de un CAPTCHA pendiente de autorización. La validación actual de las herramientas documentales conserva 28 pruebas correctas.

## Revisión documental 10, 19/10/2026

El [inventario actualizado](INVENTARIO_CASOS_REVISION10_20261019.json) conserva once candidatos y cero aptos. Se incorporaron la sentencia original de instancia y su apelación al candidato Ruta del Sol, clasificando la conducta acreditada y separando la referencia judicial de la identidad SECOP todavía no resuelta. Ver [hallazgos y exclusiones](HALLAZGOS_JUDICIALES_REV10_20261019.md). El CAPTCHA de esta consulta fue autorizado y resuelto; ese estado sustituye la espera descrita en revisiones anteriores. No se entrenaron modelos ni se cambió la publicación.

## Registro oficial SECOP consultado el 19/10/2026

Se abrió el detalle oficial de 09-1-41316 mediante navegador, separando los contratos 001 y 002. Se conservaron resolución 641, prepliego y pliego de adenda 12 con fechas del índice. La [revisión de correspondencia](CORRESPONDENCIA_SECOP_RUTA_SOL_20261019.md) distingue VPIT, presupuesto global, versiones y fechas contradictorias. Los IDs hallados en un conjunto community siguen como pistas. La [consulta de avisos de Casación Penal](AVISOS_CASACION_20261019.md) no acreditó firmeza específica. No se admitieron etiquetas ni observaciones históricas.


## Revisión documental 11, 19/10/2026

El [inventario 11](INVENTARIO_CASOS_REVISION11_20261019.json) conserva catorce registros candidatos y cero aptos. Se incorporaron Guainía y Putumayo y se separó un caso de estafa del objetivo de corrupción. Se corrigió una asociación a un PDF de otro procesado antes de admitir evidencia. La [revisión](HALLAZGOS_JUDICIALES_REV11_20261019.md) y la [validación documental](VALIDACION_CORPUS_REV11_20261019.json) conservan alcance parcial, exclusiones, hashes y cobertura corregida de años. Continúan pendientes firmeza fechada, vínculos exactos y evidencia temporal suficiente; no se entrenaron modelos ni se modificó la publicación.

## Revisión documental 12, 19/10/2026

Se ampliaron los perfiles de búsqueda histórica a Guainía y Putumayo, conservando Arauca como valor predeterminado. Las [tres lecturas completas](CORRESPONDENCIAS_HISTORICAS_GUAINIA_PUTUMAYO_20261019.json) verificaron 2.131.839 líneas y conservaron siete correspondencias candidatas, separando ocho coincidencias numéricas distintas. Se recuperaron contrato y resolución de Putumayo y resolución 0175 de Guainía. La [revisión 12](HALLAZGOS_JUDICIALES_REV12_20261019.md) documenta discrepancias de fechas, importes y disponibilidad, 37 pruebas correctas y alcance parcial. El [inventario vigente](INVENTARIO_CASOS_REVISION12_20261019.json) conserva catorce registros y cero aptos; no hay nuevas etiquetas ni modelos.

Ejemplo del perfil explícito, ejecutado desde `Backend` con un informe de salida nuevo:

```powershell
.\venv\Scripts\python.exe -m corpus_tools.scan_history --year 2015 --number 1226 --buyer-profile gobernacion-putumayo --root var\risk\judicial-discovery\secop-research\putumayo-history-2015 --output $InformeNuevo
```

El año del archivo corresponde a la convocatoria/cargue y puede diferir del año contractual: los contratos de Guainía firmados en febrero de 2013 se localizaron en el archivo 2012. La herramienta guarda candidatos; no asigna IDs al legado ni interpreta la fecha de un release con modificaciones como disponibilidad histórica de todas sus variables.

## Revisión 13: declaración posterior de firmeza, 19/10/2026

La [consulta oficial de AEP012-2024](FIRMEZA_GUAINIA_RELATORIA_20261019.json) confirma ejecutoria de SEP079-2023 en las consideraciones, pero su descarga devuelve un aviso de indisponibilidad. La política judicial v2 admite providencias posteriores con declaración expresa y fechada, manteniendo originales, hashes, revisión y vínculo específico. Las [674 pruebas backend](VALIDACION_FIRMEZA_DECLARADA_20261019.json) pasaron; las lecturas de OID 24577 y 82244 conservaron sus esquemas y no hay publicación analítica nueva. El [inventario 13](INVENTARIO_CASOS_REVISION13_20261019.json) mantiene cero aptos: el extracto parcial no se registró como prueba completa de firmeza. Ver [alcance y pendientes](HALLAZGOS_JUDICIALES_REV13_20261019.md).

## Revisión 14: expediente Centros Poblados, 19/10/2026

Se identificaron CUI 11001600000020240094600 y NI 455754 mediante ANDJE y CPNU. El registro menciona sentencia condenatoria en firme y conserva fechas distintas de actuación/registro; no tiene documentos adjuntos. La [revisión 14](HALLAZGOS_JUDICIALES_REV14_20261019.md) distingue esa anotación de una sentencia o constancia original. El [inventario](INVENTARIO_CASOS_REVISION14_20261019.json) sigue con catorce candidatos y cero aptos. La [validación documental](VALIDACION_CENTROS_POBLADOS_20261019.json) confirma hashes, exclusiones y cobertura; no hubo cambios de implementación, acceso a bases ni activación.
