# Revisión 7: correspondencia histórica investigada

El diccionario oficial de `f789-7hwg` limita su descripción a procesos registrados desde el 01/01/2018. La consulta vacía para 2012–2013 no demostraba ausencia de contratos. La [página oficial de archivos JSON de CCE](https://operaciones.colombiacompra.gov.co/transparencia/datos-json) enlaza archivos anuales anteriores.

La lectura por flujo de 2012 y 2013 terminó con CRC, tamaño y generación correctos: **1.101.679 líneas**, 3.178.404.088 bytes descomprimidos recorridos y 356.884.466 bytes comprimidos leídos. No se escribieron los archivos completos. Se conservaron dos líneas candidatas de 2013; no son dos positivos.

El [seguimiento documental](SEGUIMIENTO_VINCULO_SEP060_20261018.json) relaciona como candidato el contrato **497 del 09/10/2013**, proceso **SU-06-14-2013**, con `ocds-k50g02-13-9-372325` e identificador de adjudicación **1872157**, tal como aparecen en el archivo oficial. Se compararon fecha, entidad, objeto y contratista con las páginas 4–5 de SEP060-2025. No se asignó un ID de la base local ni se modificaron fuentes publicadas.

El contrato **362 del 31/07/2013** encontrado tiene otro objeto y contratista. No corresponde al **362 del 10/12/2012** citado en la sentencia y queda fuera de ese vínculo. Cero coincidencias en la búsqueda acotada de 2012 no prueban su inexistencia.

Se revisaron visualmente las páginas 4–6 y 263–264 del fallo. La decisión combina condena por contrato sin requisitos legales y absolución por peculado, y permite apelación. No se obtuvo firmeza ni se cerró la clasificación de conducta para entrenamiento.

El archivo incluye datos de adjudicación y terminación junto a una fecha de release anterior a la firma. **No es una observación histórica de etapa validada**: no se traslada esa fecha a todos sus campos. Tampoco se inventa una categoría a partir del objeto.

El [inventario vigente](INVENTARIO_CASOS_REVISION7_20261018.json) conserva nueve registros y cero aptos. El caso vuelve a investigación como candidato; conserva sus exclusiones pendientes y `operations` vacío. Las herramientas del corpus pasaron **27 pruebas**; no se entrenaron ni activaron modelos.
