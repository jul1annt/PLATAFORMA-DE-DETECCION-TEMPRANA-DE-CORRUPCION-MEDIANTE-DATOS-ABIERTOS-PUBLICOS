# Revisión 14 — identificación del expediente Centros Poblados

## Identidad judicial comprobada

Se identificó el proceso **11001600000020240094600**, número interno **455754**, del **Juzgado 47 Penal del Circuito con Función de Conocimiento de Bogotá**. La identificación se contrastó con dos fuentes institucionales:

- Informe de empalme ANDJE del 11/07/2024, página física 19, fila 16, que relaciona ese CUI y el anterior `11001600000020220141900` con Centros Poblados y el despacho.
- Consulta Nacional Unificada de Procesos, búsqueda completa por el CUI, con un resultado, el mismo despacho, número interno y procesado.

El PDF institucional, de 61 páginas, quedó conservado por hash. La ubicación antigua devolvió 404; se adquirió desde otra ubicación oficial encontrada, sin sustituir ni ocultar ese fallo. La fecha del informe no se usa como prueba de la fecha de publicación de su copia actual.

La consulta y sus localizadores figuran en [el seguimiento documental](SEGUIMIENTO_CENTROS_POBLADOS_20261019.json). Las referencias secundarias se utilizaron para localizar y contrastar el radicado; no se incorporaron como sentencias originales.

## Actuaciones revisadas en CPNU

Se revisaron las dos páginas que contienen 46 actuaciones. La consulta mostraba fecha de consulta **19/10/2026 17:02:45.93** y replicación **19/10/2026 16:53:10.55**.

| Fecha de actuación | Fecha de registro | Evidencia y alcance |
| --- | --- | --- |
| 19/07/2024 | 19/07/2024 | El regreso al Centro de Servicios identifica una sentencia condenatoria en firme. Es una anotación administrativa judicial; no el original de la sentencia o una constancia completa. |
| 19/07/2024 | 31/07/2024 | La anotación de individualización de pena y sentencia describe una condena por peculado y pena de 52 meses; señala que procede apelación. Se conserva separada de la anotación anterior. |
| 12/09/2024 | 12/09/2024 | Remisión de ficha técnica a ejecución de penas de Barranquilla. La remisión no fija la fecha de ejecutoria. |
| 17/04/2024 | 17/04/2024 | Ruptura de la unidad procesal procedente de `11001600010120215007900`. No se confunde esta creación de radicado con el inicio de investigación. |
| 13/11/2026 | 19/10/2026 | Audiencia de reparación futura programada hoy. No constituye una actuación ya celebrada ni una publicación posterior a la consulta. |

Una anotación de mayo de 2026 contiene referencias a otro delito, despacho y fecha interna: no se utilizó para sacar conclusiones sobre esta condena. Dos actuaciones se muestran restringidas; no se intentó acceder a ellas. El registro declara que **no posee documentos adjuntos**.

Se intentó la exportación CSV desde el control público, pero no se obtuvo un archivo local verificable. No se presenta como exportación adquirida ni se atribuye un hash de archivo inexistente. Los datos de este seguimiento proceden de revisión directa de la interfaz y del PDF institucional preservado.

## Cambios y pendientes

El candidato que antes tenía autoridad sin identificar ahora conserva el despacho, el CUI y número interno comprobados. Permanece en el mismo grupo relacionado que el auto de víctimas previamente conservado; no se cuenta como expediente positivo nuevo ni se trasladan resultados entre radicados o procesados.

El [inventario 14](INVENTARIO_CASOS_REVISION14_20261019.json) mantiene **14 candidatos y cero aptos**. La [cobertura](COBERTURA_CORPUS_REV14_20261019.json) incorpora el año contractual 2020 a este candidato; los conteos describen candidatos, no etiquetas u operaciones independientes.

Faltan la sentencia original completa, el documento de firmeza con su fecha verificable, la cronología inicial y los vínculos SECOP/evidencias por etapa. No se asignó `final_at`, no se creó etiqueta, no se entrenó y no se cambió la publicación. Esta revisión solo cambió datos y documentación; la suite backend vigente de 674 pruebas no se repitió por código inalterado. La [validación documental](VALIDACION_CENTROS_POBLADOS_20261019.json) comprueba los hashes y el inventario actualizado, sin acceso a las bases.
