# Egreso local verificado — cierre de P01

Las **seis reglas autorizadas** están aplicadas para los dos ejecutables Python dedicados. Se comprobaron en `ActiveStore`: activas, salida, bloqueo, todos los perfiles, programas/hashes correctos y conjuntos de puertos/direcciones equivalentes al plan. Los perfiles globales permanecieron iguales antes/después.

## Tráfico real

Cada Python pasó siete comprobaciones: PostgreSQL `127.0.0.1:5432`, API local y HTTPS de `www.datos.gov.co` y `datos.gov.co` accesibles; TCP externo no permitido en 443/80 rechazado con `PermissionError` y UDP externo de prueba bloqueado por timeout. El Python de desarrollo no restringido alcanzó los tres destinos externos de control. Ambas rutas HTTP de salud respondieron 200. TLS exigió certificado y hostname; no se usó proxy de entorno ni se registraron valores de filas.

Son **14 comprobaciones desde los runtimes**, **tres controles positivos** y **dos comprobaciones HTTP**. Las líneas base anteriores se conservan; los controles positivos actuales comprueban que los destinos externos seguían accesibles desde el ejecutable no restringido.

## Corrección del instalador

Windows permitió la elevación nativa, pero el proveedor CIM rechazó la representación inicial de algunos prefijos (`HRESULT 0x80070057`). Ambos intentos fallidos se conservaron y el inventario administrativo posterior confirmó cero reglas parciales y perfiles iguales. Se convirtió cada CIDR en una dirección individual o rango IPv4/IPv6. La equivalencia exacta de conjuntos se comprobó independientemente para las seis reglas; no se ampliaron ejecutables ni destinos permitidos.

[Microsoft documenta direcciones, subredes y rangos IPv4/IPv6 para `RemoteAddress`](https://learn.microsoft.com/en-us/powershell/module/netsecurity/new-netfirewallrule?view=windowsserver2025-ps). Con los rangos equivalentes, la instalación y la verificación efectiva pasaron. No se usó la salida vacía de una consulta denegada para inferir ausencia de reglas.

## Operación y alcance

Los destinos HTTPS son un snapshot DNS de los dos hosts aprobados. Revisar y renovar las direcciones de esas seis reglas si cambian los destinos; conservar evidencia anterior y volver a comprobar tráfico/definiciones antes de dar por buena una actualización. El instalador rechaza reglas previas para exigir inspección, y las verificaciones conservan sus informes sin sobrescribirlos. No se creó una automatización de cambios de firewall.

Las pruebas externas reales cubren IPv4 TCP/UDP y HTTPS. Los conjuntos IPv6 se verificaron estructuralmente y por equivalencia; no se afirma una prueba real de tráfico IPv6 externo. Las dos invocaciones de Python se comprobaron, aunque el launcher de venv usa el intérprete base para la red. La política corresponde a estos dos ejecutables y al tráfico TCP/UDP aprobado.

**P01 cerrado para el runtime local dedicado.** [Reglas efectivas, resultados, límites y hashes](EGRESO_LOCAL_VERIFICADO_20261015.json).
