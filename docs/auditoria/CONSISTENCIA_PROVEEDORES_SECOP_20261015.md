# Consistencia de proveedores SECOP — cierre local de P06

Estado: **verificado para el alcance SECOP aprobado por el usuario el 15/10/2026**. El contraste con DIAN está **no realizado**. [Criterio anterior, aprobación y criterio vigente](ALCANCE_P06_SOLO_SECOP_20261015.md).

## Universo y ejecución

Se reutilizó la copia aislada `codex_plan_full_acceptance_20261011_test`, puerto **5433**, OID **75045**, revisión `3c19a8f7e2d0`, rol ordinario `plataforma_integracion`. El corte es el **01/10/2026**. Se cotejaron **9.249.545 filas crudas y 9.249.545 procesadas**, sin filtros ni muestreo. La auditoría tomó **314.157 segundos**, incluidos los cotejos posteriores.

Se validaron hashes de los módulos del paquete `794d185832c7c56ffa4d91ef08ca1f3d15128be5`. Dos cursores recorrieron las tablas completas en orden de ID original bajo una misma transacción `REPEATABLE READ, READ ONLY`. Para cada fila se compararon referencia cruda/procesada, NIT reportado normalizado, clave derivada y nombre normalizado. También se comprobaron fuente declarada, ID Socrata presente e índice único válido de fuente/ID Socrata. Fuente conservada: `www.datos.gov.co/resource/p6dx-8zbt.json`; no hubo consultas externas nuevas.

**Discrepancias de procesamiento o procedencia: cero.** Cada fila procesada se correspondió con la fila original esperada. Los valores sin clave válida permanecen sin clave; no se completaron identificadores mediante nombres.

## Clasificación del identificador reportado

| Clasificación interna | Contratos |
| --- | ---: |
| Ausente o marcador conocido de ausencia | 8.798.585 |
| Formato aceptado sin DV reportado | 450.051 |
| Formato aceptado con DV coherente | 6 |
| Formato no admitido o ambiguo | 903 |
| DV incoherente | 0 |
| **Total** | **9.249.545** |

Estas categorías describen las reglas implementadas y el contenido reportado. Un formato aceptado no confirma existencia, titularidad ni situación tributaria histórica. El NIT y nombre de origen se conservan en la fila SECOP; las claves derivadas están separadas.

## Agrupaciones

Se derivaron **36.627 claves distintas** para **450.057 contratos**. Los conteos de **todos** los grupos coincidieron con una agregación SQL independiente por clave. Además, el método real del repositorio devolvió los **100 primeros proveedores** con claves únicas, conteos y posiciones por cantidad coincidentes con el recorrido completo.

Se encontraron **181 nombres normalizados asociados a varias claves distintas** y **320 claves asociadas a varios nombres reportados**. Las agrupaciones mantienen las claves separadas aunque coincidan los nombres. Las filas sin clave aceptada se conservan y se excluyen de las agrupaciones por NIT.

## Conservación y límites

Fuentes y trabajos estaban pausados; no había otros clientes conectados a esta copia. La auditoría emitió **cero escrituras SQL**, sin recarga, migración ni reproceso. Coincidieron los controles de fuentes/trabajos, el resumen y las huellas de las primeras 2.000 filas antes/después, incluida una transacción nueva. Estas huellas son una comprobación acotada de conservación; el cotejo de identificadores sí recorrió el universo completo. Los bindings de la aplicación publicada no cambiaron.

El clúster existente necesitó más tiempo que los 45 segundos observados inicialmente por `pg_ctl`; se confirmó el mismo proceso activo y aceptando conexiones. No se repitió el arranque. El primer preflight de auditoría se detuvo antes de leer filas por una ruta de dataset esperada incorrecta; se contrastó la ruta real con la fuente y las guardas de ingesta, conservando ambos informes.

La copia conserva los cambios derivados del ensayo previo de procesamiento/fallos. Este informe acredita consistencia en **esa copia completa**; no declara igualdad completa actual con la base publicada ni auditoría nueva de todo su contenido. No acredita identidad externa ante DIAN ni reconstruye los IDs oficiales ausentes en las 18.980 filas antiguas. P05/P12 conservan sus requisitos.

**P06 cerrado para el alcance aprobado. Plan: 98/101 completados (97,0 %), tres pendientes: P01, P05 y P12.** [Informe estructurado, conteos y hashes](CONSISTENCIA_PROVEEDORES_SECOP_20261015.json).
