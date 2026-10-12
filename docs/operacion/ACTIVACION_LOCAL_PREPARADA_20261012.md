# Activación local preparada — 12/10/2026

**Estado: preparación terminada; candidato inactivo.** Destino `plataformaanticorrupcion:5432`, OID 24577, rol ordinario `plataforma_operacion`. Backend/worker actuales `915e863`; candidato `794d185`; frontend `9362d94`. El corte publicado sigue siendo el **01/10/2026**.

## Respaldo actual y restauración comprobada

Se creó un checkpoint a las **07:28 UTC del 12/10 (02:28 Bogotá)** mediante una transacción de solo lectura, aislamiento repeatable read y snapshot exportado compartido con `pg_dump`. Se respaldaron el esquema y cuatro tablas administrativas; no se repitió el dump histórico ni una carga de contratos.

| Artefacto | Bytes | SHA-256 |
| --- | ---: | --- |
| `control-state.dump` | 25.816 | `8c57b6f61119a36ff1a333529630ad0e410e642469dd19175eac324eca2ce36a` |
| `schema-before.dump` | 72.502 | `fb9e0e1b5de8d33e71a0acf86fb37d86c095e74c5675da601c4cd93a4f945f51` |

Se copiaron configuración y exportaciones dentro de `Backend/.codex-integration-postgres/activation-preparation-20261012`, que contiene secretos y permanece privado. Los bindings activos conservaron sus hashes. Las huellas administrativas todavía coincidían al terminar la preparación; el checkpoint debe actualizarse después de congelar escrituras al ejecutar el cambio.

El ensayo restauró **1 administrador, 1 fuente, 11 sesiones y 102 trabajos** en una base temporal aislada. Coincidieron las huellas completas de las cuatro tablas; las restricciones quedaron válidas y las tres secuencias conservaron valores seguros respecto de los máximos de ID. No hubo fuentes o trabajos activos.

Los dos primeros intentos detectaron dependencias que un dump limitado por tablas no incorpora: **la colación `public.secop_source_locale` y el enum `public.tipoformato`**. Se conservaron los informes detenidos y se reutilizó la misma base temporal. Se incorporaron esas dependencias desde el respaldo de esquema verificado y se retiraron únicamente tres tablas vacías de la fase DDL interrumpida, sin `CASCADE` ni filas borradas. La restauración final se verificó a las **07:33 UTC (02:33 Bogotá)**. Después se eliminó solo la base temporal propia, OID 27055, sin sesiones; ocupaba 8.256.871 bytes. No se modificaron registros del destino publicado.

Una recuperación administrativa debe seleccionar primero la colación y el enum del TOC del esquema verificado; después restaurar las cuatro tablas y comprobar huellas, secuencias y restricciones. Una reposición sobre un destino existente exige reconciliar escrituras posteriores por claves; este ensayo no autoriza truncar o reemplazar sus tablas.

La recuperación histórica de 9.249.545 contratos conserva su prueba anterior y su dump único. Este ensayo acredita exclusivamente el checkpoint administrativo actual. [Guía de recuperación](../auditoria/GUIA_DESPLIEGUE_Y_REVERSA.md).

## Activación y reversa preparadas

Se generaron **seis archivos privados con hashes** en `activate/` y `rollback-application/`: `release.json`, `provision.json` y `runtime.env` por alternativa. Ninguno reemplazó un binding activo. `bindings-plan.json` registra hashes, identidades, versiones y comprobaciones pendientes.

La activación selecciona backend/worker `794d185` y la secuencia ensayada `f4826b9d1c30 → 08c6d9a2e4b1 → 2ab7c4e8d910 → 3c19a8f7e2d0`. Configura diez conexiones preparadas, overflow cero, espera de conexión de 60 s y búsquedas/proveedores sin workers paralelos. [Pruebas del pool y sus límites](PREPARACION_POOL_LOCAL.md).

La reversa preparada vuelve a la aplicación y los ajustes anteriores, **conservando el esquema expandido y declarando su revisión real**. No incluye downgrade automático ni restauración del histórico. Esa reversa todavía necesita ejecutarse y comprobarse durante el cambio; preparar archivos no demuestra un despliegue o una reversa ejecutados.

## Secuencia pendiente de ejecución

1. Registrar la aceptación del responsable del perfil de ocho lectores, búsqueda p95 ≤1 s y calidad ≤3 s, revisando los timeouts conservados y el alcance separado de las pruebas.
2. Coordinar el cambio, congelar escrituras, comprobar trabajos activos y pendientes, detener servicios ordenadamente y actualizar el checkpoint. Reconciliar cambios administrativos posteriores al checkpoint preparado.
3. Verificar otra vez base/puerto/OID/rol/revisión, espacio, conexiones y hashes de paquete/runtime/respaldos. Inspeccionar el índice temporal y cualquier índice inválido antes de las migraciones reanudables.
4. Aplicar las migraciones ensayadas sin recargar ni normalizar contratos. Registrar las etapas DDL confirmadas; abortar ante identidades o definiciones distintas.
5. Verificar e instalar los bindings preparados con la revisión real. Iniciar backend/worker de la misma versión y comprobar diez sesiones preparadas antes de declarar disponible la API.
6. Comprobar identidad, índices, resumen de calidad contra agregado independiente, huellas acotadas, API/interfaz/worker, autenticación, sesiones, fuentes, trabajos, búsqueda, dashboard y exportación. Registrar tiempos y errores; reanudar escrituras conforme a la decisión del corte histórico y los resultados.
7. Si procede reversa, detener servicios ordenadamente, verificar el esquema y los bindings compatibles y comprobar la aplicación anterior antes de reabrir. Ante daño de datos o incompatibilidad, mantener la pausa y preparar recuperación reconciliada.

## Pendientes de cierre

El checklist conserva **95/101 puntos completados; seis pendientes**. Esta preparación aporta evidencia a P16; no sustituye aceptación, activación ni comprobaciones posteriores. P01 necesita autorización explícita de las reglas de firewall rechazadas por revisión automática; P05/P12, identidad/extracción anterior; P06, registro DIAN autorizado; P15, aprobación y aplicación de conservación. [Registro único de pendientes](../auditoria/PLAN_DE_ACCION.md).
