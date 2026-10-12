# Activación local preparada — 12/10/2026

**Estado de esta ficha: preparación anterior a la activación.** El usuario aceptó el perfil y autorizó el cambio; backend/worker `794d185` ya están activos, con esquema `3c19a8f7e2d0`. [Activación y postflight verificados](ACTIVACION_LOCAL_VERIFICADA_20261012.md). El contenido siguiente conserva la preparación y sus límites tal como se ensayaron. Destino `plataformaanticorrupcion:5432`, OID 24577, rol ordinario `plataforma_operacion`; frontend `9362d94`; corte **01/10/2026**.

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

## Comprobaciones adicionales del destino y la reversa

El **12/10 a las 09:21 UTC (04:21 Bogotá)** se verificó el candidato contra el destino publicado, sin activarlo: identidad/OID/rol/revisión correctos, cero trabajos pendientes o en proceso, fuentes pausadas, 21 índices válidos/listos y definiciones exactas del índice anterior y del reemplazo compacto conservado. El rol ordinario tiene permiso para crear en el esquema; resumen e índice de fecha/ID siguen ausentes en este destino. Se cotejaron los 200 archivos del paquete, seis bindings preparados y dos respaldos; los ajustes propuestos pasaron validación.

Una muestra encontró `max_connections=100`, tres slots reservados, 14 conexiones cliente y **83 slots ordinarios restantes**, sin límites adicionales de rol/base. Esa muestra admite las diez conexiones de API y hasta diez del worker; debe repetirse antes de activar. Se observaron cero locks de escritura y cero sesiones ajenas con estado inaccesible. Esto es una captura puntual, no acredita que las escrituras estén congeladas.

La preparación nativa creó **diez conexiones distintas en 0,144 s** contra la base publicada con su esquema actual: diez devueltas al pool, cero prestadas, overflow cero y ajustes de transacción restaurados. El pool temporal se cerró. Las huellas UTC de las primeras 2.000 filas de crudos/procesados y el estado administrativo coincidieron antes/después; ese estado aún coincide con el checkpoint preparado. API/interfaz respondieron 200 y los bindings activos conservaron sus hashes. No se ejecutó el startup completo del candidato ni se ensayó carga concurrente en este destino.

A las **09:23 UTC (04:23 Bogotá)** se verificó la aplicación anterior `915e863` contra el esquema ampliado `3c19a8f7e2d0`, en la copia completa ya existente, OID 75045, puerto 5433. Sus **186 archivos** se compararon con el archivo Git de esa revisión y el lock coincidió con el runtime. Se inició solo su API en loopback:8797, forzando todas sus transacciones SQL a solo lectura. Ocho solicitudes, dos por ruta, respondieron 200: búsqueda de 2024 (1.670.370 resultados, página de 20), búsqueda vacía, calidad y proveedores. Calidad/proveedores coincidieron exactamente con las referencias del candidato. Las dos páginas de búsqueda no coincidieron por contenido con el candidato: la versión anterior carece del desempate por ID; se comprobó su total/tamaño, no equivalencia completa de esa página.

Los tiempos individuales de ese ensayo no son un perfil de carga ni una medición p95. No se iniciaron worker ni pruebas de mutación de autenticación/exportación. Huellas acotadas, resumen y último trabajo conservaron sus valores; el servidor terminó y las configuraciones publicadas no cambiaron. **Esto acredita compatibilidad HTTP de lectura de la reversa en la copia; no una reversa ejecutada en el destino publicado ni equivalencia de todo su comportamiento.** [Informe estructurado de ambas comprobaciones](ACTIVACION_LOCAL_COMPROBACIONES_20261012.json).

## Pasos de ejecución

1. Registrar la aceptación del responsable del perfil de ocho lectores, búsqueda p95 ≤1 s y calidad ≤3 s, revisando los timeouts conservados y el alcance separado de las pruebas.
2. Coordinar el cambio, congelar escrituras, comprobar trabajos activos y pendientes, detener servicios ordenadamente y actualizar el checkpoint. Reconciliar cambios administrativos posteriores al checkpoint preparado.
3. Verificar otra vez base/puerto/OID/rol/revisión, espacio, conexiones y hashes de paquete/runtime/respaldos. Inspeccionar el índice temporal y cualquier índice inválido antes de las migraciones reanudables.
4. Aplicar las migraciones ensayadas sin recargar ni normalizar contratos. Registrar las etapas DDL confirmadas; abortar ante identidades o definiciones distintas.
5. Verificar e instalar los bindings preparados con la revisión real. Iniciar backend/worker de la misma versión y comprobar diez sesiones preparadas antes de declarar disponible la API.
6. Comprobar identidad, índices, resumen de calidad contra agregado independiente, huellas acotadas, API/interfaz/worker, autenticación, sesiones, fuentes, trabajos, búsqueda, dashboard y exportación. Registrar tiempos y errores; reanudar escrituras conforme a la decisión del corte histórico y los resultados.
7. Si procede reversa, detener servicios ordenadamente, verificar el esquema y los bindings compatibles y comprobar la aplicación anterior antes de reabrir. Ante daño de datos o incompatibilidad, mantener la pausa y preparar recuperación reconciliada.

## Pendientes de cierre

El checklist conserva **95/101 puntos completados; seis pendientes**. Esta preparación aporta evidencia a P16; no sustituye aceptación, activación ni comprobaciones posteriores. P01 necesita autorización explícita de las reglas de firewall rechazadas por revisión automática; P05/P12, identidad/extracción anterior; P06, registro DIAN autorizado; P15, aprobación y aplicación de conservación. [Registro único de pendientes](../auditoria/PLAN_DE_ACCION.md).
