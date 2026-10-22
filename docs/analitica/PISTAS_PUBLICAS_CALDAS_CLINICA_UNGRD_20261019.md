# Seguimiento público: Caldas, clínica de Bogotá y UNGRD

Fecha: 19/10/2026, Bogotá. Solo consulta y adquisición pública; ningún contacto con terceros.

## Documentos efectivamente conservados

Catálogo: [fuentes seleccionadas](fuentes_pistas_publicas_20261019.json). Recibo del recolector: `Backend/var/risk/judicial-discovery/runs/20261019T230557483925Z.json`, dos fuentes, cero errores, cero etiquetas y sin acceso a bases. Los cuerpos están en `Backend/var/risk/judicial-discovery/objects/<sha256>`.

| Fuente | SHA-256 | Alcance |
| --- | --- | --- |
| Índice 2022 del Juzgado 18 de garantías de Bogotá | `d18248e28a1972f476e254fca4ef74888e55d33accd4e6ae253e6b2f7a3ca485` | HTML público adquirido; referencia a una actuación, no sentencia |
| Acta de reparto penal de la Corte del 03/08/2021 | `63dd0673cf17a41bc69294d73c1b3459d5036d9ca75ebd3afddda0ae3a531fde` | PDF público adquirido; revisión física de página 11; no sentencia |

## Escuela Taller de Caldas

El [índice judicial oficial](https://www.ramajudicial.gov.co/web/juzgado-018-penal-municipal-con-funcion-de-control-de-garantias-de-bogota/51), fila del 30/07/2022, identifica CUI `11001600010120205015900`, NI `395287`, y una actuación de legalización para James Peña Garzón y otra persona. El enlace al acta es una ruta relativa que devolvió 404 al abrirla; no se conserva un acta inexistente como archivo adquirido.

La [noticia de descubrimiento](https://caracol.com.co/2025/06/19/exdirector-de-la-escuela-taller-de-caldas-es-condenado-el-caso-de-corrupcion-las-marionetas/?outputType=amp) señala proyectos de 2020–2022 y una condena de 2025. Falta la sentencia original, su CUI específico tras posibles rupturas y firmeza. No se identifica ese CUI con el de la condena por inferencia. La fecha de legalización y el año del CUI tampoco prueban inicio de investigación. Debe comprobarse relación con el grupo Mario Castaño existente antes de contar expedientes independientes.

## Interventoría de clínica en Bogotá

El [acta oficial de reparto](https://cortesuprema.gov.co/corte/wp-content/uploads/not/penal21/actarepartopenal03082021.pdf) permite localizar una tutela a nombre de Nidia Esperanza Garzón Morales, CUI `11001020400020210159100`, interno `118533`. No es el radicado de una condena penal. La [transcripción secundaria de STC1703-2022](https://vlex.com.co/vid/sentencia-corte-suprema-justicia-898627720) remite a un proceso penal 2019-00128; no se descargó ni admitió original de esa tutela o de la sentencia penal.

El resultado indexado del [informe institucional de Subred Norte](https://www.subrednorte.gov.co/wp-content/planeacion/informe_empalme_dr_daniel_blanco.pdf) contiene CUI `11001600000020190012800` y estado «lectura de sentencia». Ese informe no se adquirió en esta ejecución; no se trata el resultado del buscador como un original local. Falta verificar la relación concreta con el contrato de la clínica, la condena y su firmeza. Una tutela, un informe de gestión y una noticia no sustituyen esas comprobaciones.

## UNGRD

La [pista periodística sobre López Rosero](https://focusnoticias.com/seis-anos-de-prision-para-el-contratista-luis-eduardo-lopez-rosero-por-corrupcion-en-la-ungrd/) orienta hacia una condena de junio de 2025 y contratación de 2023. No se obtuvo sentencia original ni constancia de ejecutoria. Las búsquedas por nombre devolvieron también tutelas de otras personas y repartos: se descartan para etiquetar esta operación. No se usa el radicado de una tutela del mismo nombre como radicado de condena.

La referencia `SMD-GS-CTQ-192-2023` hallada en otra decisión reproducida por un tercero permanece como pista contractual no verificada; no se asignó a ninguna fila SECOP. Las decisiones relativas a otros investigados tampoco trasladan su resultado a este candidato.

## Resultado y siguiente comprobación

Se adquirieron dos fuentes oficiales de descubrimiento y se acotaron referencias procesales. No se adquirió ninguna sentencia condenatoria nueva. Las tres pistas quedan fuera del registro canónico hasta comprobar originales y relaciones; no son tres positivos nuevos, ni tres expedientes independientes confirmados.

La búsqueda siguiente debe usar los radicados y referencias anteriores en publicaciones públicas accesibles, distinguir rupturas, recursos y contratos concretos, y conservar las limitaciones cuando el documento no esté publicado. No se contactará a las entidades. No se ejecutaron entrenamiento ni pruebas de código inalterado. La publicación sigue condicionada a evidencia y validación reales.

## Comprobación posterior por radicado

Se buscaron literalmente `11001600000020190012800`, `11001600010120205015900`, `STC1703-2022` y la referencia a firmeza de la condena de López Rosero. Los resultados relevantes recuperaron el índice judicial y la transcripción de tutela ya identificados; no se obtuvo sentencia penal original nueva. Esto describe el alcance de estas consultas y no demuestra que no existan otros documentos públicos.

Se renderizó y examinó la página física 11 del acta de reparto conservada: grupo 20, tutela de primera instancia; proceso `11001020400020210159100`, interno `118533`, secuencia `5075`, reparto 03/08/2021. La revisión confirma la separación entre radicado de tutela y proceso penal. No se revisaron físicamente las otras trece páginas ni se atribuye resultado penal al acta. Imagen local de revisión: `Backend/tmp/pdfs/reparto-20210803-review/page-011.png`.

La carencia de positivos admitidos persiste tras tres turnos de búsqueda exclusivamente pública. Con los documentos obtenidos no se pueden entrenar los dos modelos, demostrar mejora estadística ni completar su aceptación operativa. No se sustituirá la evidencia faltante con noticias, tutelas, agendas o fixtures. Los bloqueos de acceso permanecen respetados y los contactos institucionales están expresamente descartados.
