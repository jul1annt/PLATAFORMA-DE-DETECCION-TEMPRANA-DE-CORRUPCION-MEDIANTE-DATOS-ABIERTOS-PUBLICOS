# Cinco pendientes después de la activación local

Estado: **96/101 completados; cinco abiertos**. Backend/worker `794d185` ya se activaron y P16 quedó cerrado para el perfil aceptado. [Despliegue verificado](ACTIVACION_LOCAL_VERIFICADA_20261012.md). Esta continuación revisa conservación y condiciones del firewall; no vuelve a probar el recorrido completo ni declara resueltas identidades ausentes.

**Actualización posterior:** el usuario aprobó conservación y autorizó las seis reglas. P15 quedó cerrado con aplicación comprobada; Windows canceló la elevación antes de iniciar el helper de firewall. Estado vigente **97/101, cuatro pendientes**. [Constancia y comando administrativo](CONSERVACION_APROBADA_Y_EGRESO_20261012.md). El contenido restante y su JSON conservan esta revisión anterior a las decisiones.

## Conservación: revisión sin borrados

Se comprobó la presencia de **ocho respaldos históricos**, 12.979.002.521 bytes en total, y los checkpoints de esquema/control actuales y anteriores. Se cotejaron hashes de los checkpoints pequeños; no se recalcularon los dumps grandes ni se repitieron sus restauraciones. Los artefactos activos `794d185` y anteriores `915e863` siguen presentes; los bindings activos conservaron sus hashes.

La copia derivada `codex_plan_full_acceptance_20261011_test:5433`, OID 75045, esquema `3c19a8f7e2d0`, ocupa **23.077.412.199 bytes**. Tenía cero sesiones, trabajos activos y fuentes activas. Su prefijo de 2.000 filas crudas UTC coincide con el origen conservado `plataforma_integracion_local`, OID 74053; las comprobaciones completas y la terminación de los ensayos se reutilizan desde sus informes. El origen ocupa 23.158.209.895 bytes.

**Se conserva la copia derivada:** P06 todavía exige comprobar identidad histórica en una copia aislada. Hasta conocer el archivo DIAN autorizado y el alcance exacto de esa comprobación, retirar esta copia podría obligar a crearla otra vez. La ausencia de sesiones no basta para considerarla sin uso. No se borraron bases, registros, archivos ni respaldos.

La [política propuesta](RETENCION_LOCAL_PROPUESTA.md) mantiene generaciones únicas, originales e historial mientras no se demuestre la identidad anterior. El usuario recibió la pregunta de aprobación de ese alcance. P15 necesita aprobación y constancia de aplicación; P05 necesita además la evidencia de identidad antigua. El bloqueo previo del retiro del paquete `6c63b309a278` permanece separado y no se elude.

## Firewall: condiciones previas

La inspección de solo lectura encontró los tres perfiles de Windows Firewall habilitados y **cero reglas `PDTC-Local-*`**. El proceso actual no está elevado. No se cambiaron perfiles ni se aplicaron reglas.

Se solicitó autorización explícita para las seis reglas ya preparadas, limitadas a los dos ejecutables Python del runtime dedicado: bloquear TCP/UDP externos, permitir HTTPS a IP verificadas de `datos.gov.co` y conservar conexiones locales PostgreSQL/API. La revisión automática anterior rechazó ese cambio por faltar autorización para su alcance. Si el usuario lo autoriza, actualizar resolución DNS/hashes, aplicar con privilegios administrativos y verificar desde ambos ejecutables bloqueo real y conectividad permitida. La instalación de reglas por sí sola no cierra P01.

## Qué falta por punto

| Punto | Requisito pendiente |
| --- | --- |
| P01 | Autorización explícita de las seis reglas, aplicación administrativa y prueba efectiva de red. |
| P05 | Aprobar conservación del historial y explicar cambios anteriores con evidencia de identidad/extracción. |
| P06 | Ruta al registro DIAN autorizado; contraste histórico en copia aislada, con coincidencias y límites. |
| P12 | Ruta a extracción/log antiguo que conserve IDs oficiales de las 18.980 filas; investigar el detalle individual ya preparado sin inferir IDs por contenido. |
| P15 | Aprobar la política conservadora y registrar su aplicación sobre el inventario comprobado. |

Se pidieron rutas locales de los dos insumos de identidad. No se afirma que esos archivos no existan en el equipo: todavía no fueron facilitados. [Registro único del plan](../auditoria/PLAN_DE_ACCION.md).

Evidencia restringida de esta revisión: `Backend/.codex-integration-postgres/retention-preparation-20261012/inventory.json` y `firewall-prerequisites.json`. [Resumen público estructurado](PENDIENTES_LOCALES_20261012.json). Las decisiones y preguntas pendientes no se consideran aceptadas por silencio.
