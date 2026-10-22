# Cierre con limitación histórica aceptada — P05 y P12

Estado: **aceptado por el usuario el 15/10/2026**, mediante «Aceptar la limitación histórica». La comprobación posterior del original, el informe individual y los respaldos pasó; **P05/P12 cerrados para este alcance y checklist 100/101**. Esta aceptación sustituye sus criterios de cierre y no acredita conciliación histórica completa. [Verificación y límites](CIERRE_LEGADO_SECOP_ACEPTADO_20261015.md).

## Evidencia disponible

El usuario confirmó el 15/10/2026: «No, solo están los contratos guardados», al preguntar por una exportación o bitácora antigua con IDs oficiales SECOP. El original de 18.980 filas se conserva; carece de la columna de identidad Socrata. Los respaldos y comparaciones documentados siguen protegidos por la política conservadora aprobada.

Se revisó la página pública oficial de [SECOP II — Procesos de Contratación](https://www.datos.gov.co/Estad-sticas-Nacionales/SECOP-II-Procesos-de-Contrataci-n/p6dx-8zbt/about_data). Su sección «Registro de cambio del conjunto de datos» mostró **«Aún no se han archivado cambios»**. La consulta fue anónima y de lectura. Este resultado describe el historial visible; no demuestra que el publicador carezca de archivos internos o versiones ocultas.

La [documentación de Socrata sobre archivos de versiones](https://support.socrata.com/hc/en-us/articles/9486838238743-Introducing-Dataset-Archiving) explica que esta función requiere habilitación y permite exportar versiones archivadas accesibles. No se obtuvo una versión anterior exportable desde la página examinada. No se activó archivado, se generó una exportación ni se cambió nada en el portal.

## Qué se sabe y qué sigue sin demostrarse

El [detalle de linaje existente](LINAJE_LEGADO.md) compara los 18.980 registros antiguos con 105.640 candidatas del corte aceptado del 01/10/2026:

| Comparación de contenido | Filas antiguas |
| --- | ---: |
| Coincidencia exacta única en 60 campos | 15.392 |
| Coincidencia exacta con varias candidatas | 118 |
| Sin coincidencia exacta | 3.470 |
| **Total** | **18.980** |

Las tuplas de adjudicación produjeron, como clasificación alternativa, 18.115 coincidencias únicas, 157 ambiguas y 708 ausentes. Estas categorías no se suman a las anteriores. El informe del 30/09 conserva sus propios resultados y no se mezcla con este corte.

**La identidad oficial anterior sigue sin demostrarse para las 18.980 filas**, incluidas las que tienen contenido idéntico. Las diferencias no permiten atribuir por sí solas la causa a una modificación de la fuente, un reemplazo de generación o el procesamiento antiguo. Se asignaron cero IDs oficiales inferidos.

## Criterios originales conservados

- **P05:** reconciliar modificaciones anteriores al versionado y cambios fuera de ventana o causados por reemplazos completos.
- **P12:** resolver el linaje de las filas sin coincidencia exacta, tuplas ambiguas y cambios de atributos antes de declarar conciliación histórica total, sin inferir identidad por proceso/adjudicación.

Esos resultados completos no están acreditados por los insumos disponibles.

## Criterios de sustitución aceptados

### P05 — cerrar la investigación previa con limitación explícita

Conservar y verificar la referencia al original, sus respaldos y las comparaciones disponibles; documentar los cambios de contenido observados y sus causas no demostradas. Mantener la medición de crecimiento del historial y la política de conservación ya aprobadas. Registrar que el historial anterior al mecanismo de versionado no se pudo reconstruir y que los cambios futuros se documentarán solo cuando sean observados por dicho mecanismo.

El corte aceptado del **01/10/2026** es la línea de base publicada. No acredita una captura continua desde esa fecha: las fuentes siguen pausadas y no se inventarán versiones de intervalos no observados.

### P12 — conservar todos los casos como legado no conciliado

Mantener el original y el detalle individual de las 18.980 filas, sus cardinalidades y diferencias, con conteos reproducibles y hashes. Dejar la identidad anterior expresamente no demostrada; conservar separados los registros antiguos y el corte publicado, sin asignar IDs por similitud ni unir historiales de generaciones por conjetura.

El entregable sería el cierre documentado de la investigación **con legado no conciliado**, aceptado como límite del proyecto. No se presentaría como conciliación histórica total.

## Comprobaciones requeridas y realizadas

- Cotejar los hashes del informe individual y la presencia/identidad de los originales y respaldos protegidos, reutilizando la evidencia existente.
- Comprobar que los conteos individuales corresponden a las 18.980 filas y a sus clasificaciones alternativas, que las listas truncadas no se presentan como listas completas y que no se asignaron identidades oficiales.
- Registrar la aceptación exacta y el alcance sustituido junto a la limitación. Mantener el corte, los datos y los respaldos conservados; no recargar ni reprocesar el universo.
- Actualizar el plan únicamente después de esas comprobaciones. P01 conserva su instalación administrativa y prueba efectiva de firewall.

## Decisión recibida

El usuario aceptó expresamente este ajuste después de confirmar la ausencia de exportaciones/bitácoras antiguas y de conocer el resultado del historial público. P05/P12 se cierran como investigación con legado no conciliado, tras verificar los entregables de conservación y diagnóstico. Las 18.980 identidades anteriores siguen no demostradas. P01 permanece abierto.
