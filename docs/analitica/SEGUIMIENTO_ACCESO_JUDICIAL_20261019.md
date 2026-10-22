# Seguimiento de acceso a evidencia judicial

## Instrucción vigente: exclusivamente información pública

El 19/10/2026 el usuario indicó que no puede cambiar los permisos y prohibió expresamente contactar a terceros. Las solicitudes propuestas quedaron descartadas y nunca se enviaron. No hay autorización de envío pendiente ni se solicitarán datos personales para esos borradores. La investigación continuará mediante documentos ya públicos en fuentes accesibles, sin eludir los bloqueos guardados. La disponibilidad de un original completo no implica que el caso sea admisible: siguen vigentes firmeza fechada, alcance por operación y evidencia temporal.

La [búsqueda pública posterior](BUSQUEDA_PUBLICA_20261019.md) conserva las pistas y su alcance. No produjo etiquetas ni cambios del registro canónico.

Se investigó una pista de contratación de 2020–2021 en la I.E. San Felipe Neri de Cartagena. No se adquirió la sentencia original ni se verificaron firmeza, radicado o contratos exactos. La pista queda separada del registro canónico; no aumenta el número de expedientes candidatos ni constituye una etiqueta positiva.

La búsqueda institucional actual en Fiscalía no devuelve coincidencias. El resultado indexado por el buscador remite a una página paginada cuyo contenido actual no permite adquirir el comunicado concreto. No se trata el resumen del buscador como un comunicado original y la falta de coincidencia no prueba inexistencia del proceso.

## Autorización y bloqueo de la herramienta

El usuario autorizó expresamente la consulta de CPNU y del repositorio de providencias de la Corte, y la descarga de documentos públicos de SECOP II. Después de esa autorización se intentó nuevamente el acceso normal, una vez por origen:

| Origen | Respuesta de la herramienta |
| --- | --- |
| `consultaprocesos.ramajudicial.gov.co` | Bloqueo por permiso guardado o política administrada |
| `consultaprovidencias.cortesuprema.gov.co` | Bloqueo por permiso guardado o política administrada |
| `community.secop.gov.co` | Permiso del origen denegado |

La autorización por mensaje está recibida; el ajuste externo de permisos de la herramienta continúa pendiente. Se solicitó retirar el bloqueo guardado o acudir a su administrador. No se accedió a esos orígenes mediante herramientas alternativas después de sus rechazos.

## Corrección independiente de recolección

Durante esta investigación un catálogo omitió `kind`. El recolector guardó correctamente un cuerpo y su entrada de ledger, pero luego falló con `KeyError` antes de generar el recibo de ejecución. Se corrigió el catálogo y se reutilizó el cuerpo conservado. Después se reforzó el recolector para validar toda la selección antes de iniciar cualquier descarga o escritura: estructura, campos obligatorios, URLs y duplicados.

Las pruebas nuevas verifican que un catálogo inválido, incluso cuando el error está en la segunda fuente, no descarga archivos ni crea directorios. Las herramientas de adquisición, historial y almacenamiento pasaron **39 pruebas**. No cambió código de API, entrenamiento o inferencia; la última batería completa del backend continúa siendo la de 744 pruebas ya documentada, no repetida en esta revisión.

El [registro estructurado](DESCUBRIMIENTO_CARTAGENA_NERI_20261019.json) conserva recibos, hashes, resultados y límites. Se volvió a ejecutar el validador del corpus: **14 candidatos, cero aptos**. El registro canónico conserva el mismo hash; no hubo acceso a bases de datos, entrenamiento ni publicación.
