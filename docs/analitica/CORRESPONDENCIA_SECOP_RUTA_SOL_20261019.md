# Registro oficial y documentos históricos de Ruta del Sol

## Acceso y procedencia

El 19/10/2026 se abrió mediante el navegador el [detalle oficial de SECOP I](https://www.contratos.gov.co/consultas/detalleProceso.do?numConstancia=09-1-41316). Las consultas anteriores mediante la herramienta web no habían permitido leerlo; esa limitación no significa que el registro esté ausente. No se utilizaron credenciales ni se resolvió un nuevo CAPTCHA.

Una consulta acotada de descubrimiento a `x6v4-i8gf` devolvió seis filas: cinco repiten el UID del contrato 002 y una corresponde al 001. La procedencia declarada de ese conjunto es **community**. Sus identificadores se conservan únicamente como pistas: `1536756` para el 001 y `1733414` para el 002. No se asignaron como identidades oficiales verificadas al corpus ni al corte publicado.

## Contratos distintos en un mismo proceso

El detalle oficial distingue el **contrato 001**, Concesionaria Ruta del Sol S.A.S., de **002**, Consorcio Vial Helios. Ambos muestran firma el 14/01/2010. La cuantía que muestra el primer contrato es $2.094.286.000.000 y la del segundo $962.075.973.782. El proceso contiene una cuantía global de $5.700.000.000.000: no se sustituye con ella el importe individual ni se trata una fecha compartida como duplicidad.

El contrato 001 concuerda documentalmente con la referencia jurídica identificada en la apelación penal. La pantalla consultada no mostró el ID numérico de adjudicación candidato. Se mantiene pendiente la correspondencia del identificador de fila/adjudicación del conjunto de entrenamiento. No se etiqueta todo el proceso, el contrato 002 o el proveedor.

## Documentos conservados

La [adquisición estructurada](DOCUMENTOS_SECOP_RUTA_SOL_20261019.json) conserva nombres, hashes, tamaños y fechas mostradas por el índice oficial:

| Documento | Páginas | Publicación mostrada por SECOP |
| --- | ---: | --- |
| Resolución 641, documento 1456887 | 6 | 18/12/2009, 18:09 |
| Proyecto de pliego, documento 959284 | 105 | 10/03/2009, 00:34 |
| Pliego de adenda 12, documento 1323952 | 125 | 22/10/2009, 00:02 |

La zona Bogotá se declara como interpretación del horario local mostrado, no como metadato explícito del servidor. Son fechas observadas hoy en el índice y requieren revisión temporal antes de admitir variables históricas.

El prepliego tiene exactamente el mismo SHA-256 que la copia antes recuperada de ANI: `8ae976fa9a3f2edcd83d3bc99a8944eadd1893d7d1312801c73b1e7b7a20fcd9`. La nueva procedencia corrobora la identidad del cuerpo y aporta la fecha mostrada por SECOP; no prueba disponibilidad el 09/03/2009.

La descarga del pliego definitivo 987089 no produjo un archivo confirmado, también al esperar su evento de descarga. Se registra ese fallo y no se equipara automáticamente con el documento ya conservado de ANI. El enlace al reporte de modificaciones tampoco mostró un reporte verificable en esta consulta.

## Resolución y cronología

Se revisaron visualmente las páginas 1, 5 y 6 de la resolución 641, SHA-256 `bd7d800f3cf01fbd85e9a363c64a0da7dd98236a41e4df455facc275898dbc92`. El artículo primero adjudica el sector 2 al proponente 3, promesa de sociedad futura Concesionaria Ruta del Sol. El segundo expresa **VPIT en pesos del 31/12/2008**: $2.094.286.000.000. No se transforma en importe nominal comparable sin tratamiento monetario explícito. Los artículos cuarto y quinto tratan notificación y recursos del acto administrativo; **no acreditan firmeza de la condena penal**.

Se revisaron visualmente las páginas físicas 28–30 del pliego de adenda 12, SHA-256 `4b685ccf5f4784cb4860706e92e8e2cffb2744ad8e1cbc32048b97fc85f8f037`. El cronograma contiene cierre previsto el 27/10/2009 a las 15:00 y adjudicación prevista el 11/12/2009. La resolución efectiva es del 15/12/2009. No se reemplazan fechas previstas con efectivas sin conservar su significado y versión.

La página 28 refiere apertura el 27/03/2009; la ficha actual muestra 24/03/2009. Los hitos informáticos del portal muestran adjudicación registrada en enero de 2010 y celebración registrada en 2013. Esos registros de carga no son fechas de los hechos contractuales. Las diferencias quedan explícitas para la revisión de cada variable.

## Resultado

Se resolvió el acceso al registro oficial y se amplió la evidencia de adjudicación y versiones. Faltan identidad de fila/adjudicación corroborada, revisión completa, firmeza penal fechada y observaciones por etapa admitidas. La [revisión 10 del inventario](INVENTARIO_CASOS_REVISION10_20261019.json) sigue con once candidatos y cero aptos. No se cambió la base de contratos, no se entrenaron modelos ni se activó publicación.

## Comprobación adicional del identificador

La consulta exacta de constancia al conjunto oficial f789-7hwg devolvió cero filas el 19/10/2026. Se conservó el recibo ruta-sol-official-lookup-20261019.json y el cuerpo vacío por hash en el directorio privado de investigación. Este resultado no prueba ausencia del contrato ni valida el ID de la fuente community: el detalle oficial del proceso sí fue leído. Se mantiene pendiente la corroboración numérica.

