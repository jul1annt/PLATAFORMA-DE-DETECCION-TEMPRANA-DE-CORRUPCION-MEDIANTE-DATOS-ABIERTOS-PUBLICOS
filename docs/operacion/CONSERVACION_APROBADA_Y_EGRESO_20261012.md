# Conservación aplicada y egreso autorizado — 12/10/2026

## Decisiones recibidas

El usuario aprobó **«Aprobar la política conservadora»** y **«Autorizar esas seis reglas locales»**. La autorización del firewall ya está resuelta; falta que Windows permita la ejecución administrativa y comprobar las reglas efectivas. [Informe estructurado](CONSERVACION_APROBADA_Y_EGRESO_20261012.json).

## P15: política aprobada y aplicada

La política quedó registrada y aplicada a las **20:12 UTC del 12/10 (15:12 Bogotá)**. Se preservan originales, generaciones únicas, historial SECOP, los ocho respaldos históricos y los artefactos de la aplicación activa/anterior. Se inventariaron **34 bases locales**, sin retirar ninguna; el inventario conserva también elementos cuyo uso aún no está resuelto, sin presumir que son generaciones únicas o copias eliminables. La copia completa de ensayo OID 75045 sigue disponible para P06.

Se comprobó la presencia/tamaño de los ocho dumps grandes y se reutilizaron sus verificaciones anteriores. Los hashes de los checkpoints pequeños se cotejaron nuevamente. No se repitió una restauración o un respaldo histórico completo.

Se creó un checkpoint adicional del estado administrativo actual, usando un snapshot PostgreSQL consistente compartido con `pg_dump`, con servicios funcionando. Comprende **1 administrador, 1 fuente, 12 sesiones y 103 trabajos**, más esquema actual, configuración y la exportación CSV de prueba. Las huellas administrativas coincidieron después de copiar; un snapshot no congela futuras escrituras y una recuperación debe reconciliarlas.

| Respaldo pequeño nuevo | Bytes | SHA-256 |
| --- | ---: | --- |
| `control-state.dump` | 26.053 | `338026c60e49aa696a485c973afe75dfb01b6c78363d3566b7f3584b394b8b8c` |
| `schema-current.dump` | 83.103 | `985127ceba5fb93e392edef49346dfd257362d7aa6b24e607c0fb804eec2ec69` |

Los archivos se conservan en el directorio privado `Backend/.codex-integration-postgres/security-retention-application-20261012/current-control-checkpoint/`. Las dependencias de restauración administrativa son la colación `secop_source_locale` y el enum `tipoformato`; se reutiliza el ensayo de restauración verificado y la equivalencia del esquema de esas cuatro tablas. No se afirma que estos dos archivos nuevos hayan sido restaurados otra vez.

**P15 cerrado.** La decisión de conservar el historial también queda resuelta para P05; la identidad anterior al versionado sigue pendiente. Se registró revisión manual del inventario para el **19/10**, y al recibir insumos de identidad o cerrar P05/P06/P12. No hay vencimientos automáticos ni se creó una automatización de borrado. Bases, filas y archivos eliminados: **cero**.

## P01: autorización recibida, instalación pendiente de Windows

Se renovaron las IP de `www.datos.gov.co`/`datos.gov.co` y los hashes de los dos Python dedicados. Antes de aplicar reglas, ambos ejecutables pasaron siete comprobaciones cada uno: PostgreSQL/API locales, HTTPS de ambos hosts oficiales con certificado y hostname verificados, TCP externo no permitido en 443/80 y una consulta DNS UDP externa. Todas fueron accesibles en la línea base; no hubo extracción completa ni sincronización de fuentes.

Se intentó iniciar el helper administrativo con ventana oculta, limitado a las seis reglas aprobadas. **Windows informó cancelación de la elevación antes de iniciar el helper.** No se crearon reglas, no cambió ningún perfil global y no se hizo una prueba posterior de bloqueo. El rechazo automático anterior por falta de autorización queda resuelto por la instrucción explícita; esta cancelación es un requisito de privilegios de Windows distinto.

La instalación exige `#Requires -RunAsAdministrator` en `apply_local_egress.ps1`. Se pidió elegir entre reintentar la elevación confirmándola en Windows o ejecutar el comando en PowerShell como administrador. No se vuelve a pedir autorización del alcance de las seis reglas.

El reintento solicitado mediante «Continúa» también terminó con cancelación de Windows antes de iniciar el helper. La sesión es interactiva, pero el token del proceso no está elevado ni contiene el grupo de administradores. Siguen existiendo cero reglas nuevas y no hay un registro de instalación administrativa. El diagnóstico corresponde al token del proceso de ejecución.

### Un solo comando para instalar y verificar

Abrir **PowerShell como administrador** y ejecutar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS\Backend\.codex-e2e-postgres\install_and_verify_approved_egress_20261012.ps1"
```

El entrypoint actualiza DNS/hashes, instala únicamente las seis reglas autorizadas y ejecuta las pruebas de tráfico. Su sintaxis se comprobó sin ejecutarlo; `#Requires` impide usarlo desde un terminal sin privilegios. Si ya hay reglas o una ejecución parcial registrada, se detiene para preservar la evidencia. Al terminar correctamente deja `firewall-verified.json`; hasta comprobar ese resultado P01 sigue abierto.

### Comando preparado para PowerShell como administrador

```powershell
Set-Location -LiteralPath 'C:\PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS'
& .\Backend\venv\Scripts\python.exe .\Backend\scripts\prepare_local_egress.py --root .\Backend\.codex-integration-postgres
& .\Backend\.codex-e2e-postgres\apply_approved_egress_20261012.ps1 -IntegrationRoot .\Backend\.codex-integration-postgres
```

Actualizar DNS justo antes del cambio evita aplicar el plan preparado vencido. El helper rechaza identidades distintas, reglas ya presentes y ejecuciones anteriores registradas; conserva el resultado en `firewall-execution.json`. Si existe una ejecución parcial/fallida, inspeccionar antes de repetir. Instalar reglas no cierra P01: falta verificar definiciones efectivas y probar desde ambos ejecutables HTTPS permitido, TCP/UDP bloqueados y PostgreSQL/API locales conservados, con un control no restringido y perfiles globales iguales.

Las reglas autorizadas filtran IP/puerto/protocolo del runtime dedicado; sus IP son un snapshot DNS que debe actualizarse ante cambios del destino. No cambian los perfiles globales ni otros ejecutables. La validación posterior debe declarar familias de direcciones y transportes realmente probados.

## Estado del plan

**97/101 completados (96,0 %), cuatro pendientes (4,0 %): P01, P05, P06 y P12.** P01 necesita ejecución administrativa y prueba efectiva; los otros tres siguen esperando el registro DIAN autorizado y/o extracción histórica con IDs oficiales. La política no demuestra identidad ni autoriza inferir IDs por contenido. [Plan vigente](../auditoria/PLAN_DE_ACCION.md).
