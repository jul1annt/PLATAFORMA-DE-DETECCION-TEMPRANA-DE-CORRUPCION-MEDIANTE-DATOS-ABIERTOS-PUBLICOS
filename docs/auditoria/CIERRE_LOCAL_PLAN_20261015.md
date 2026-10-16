# Cierre local del plan — 15/10/2026

**101/101 requisitos verificados para el alcance acordado; cero pendientes.** [Plan](PLAN_DE_ACCION.md), [matriz de los 101 requisitos, evidencias y hashes](CIERRE_LOCAL_PLAN_20261015.json).

## Resultado

- **P01:** seis reglas del runtime dedicado aplicadas y verificadas; 14 comprobaciones de tráfico, tres controles positivos y dos rutas de salud pasaron. SECOP/PostgreSQL/API accesibles, TCP/UDP externo no permitido bloqueado y perfiles globales iguales. [Egreso y límites](../operacion/EGRESO_LOCAL_VERIFICADO_20261015.md).
- **P06:** auditoría completa de 9.249.545 filas crudas y procesadas en la copia aislada, cero discrepancias y 36.627 claves/agrupaciones verificadas. Alcance SECOP aprobado; identidad DIAN no contrastada. [Resultados](CONSISTENCIA_PROVEEDORES_SECOP_20261015.md).
- **P05/P12:** investigación cerrada con limitación histórica expresamente aceptada. Original y 18.980 casos verificados; las identidades anteriores siguen no demostradas y el legado no está conciliado. Ocho respaldos protegidos conservados y respaldo pequeño original comprobado por SHA-256. [Aceptación y conservación](CIERRE_LEGADO_SECOP_ACEPTADO_20261015.md).

## Auditoría de cierre

Se revisaron las 101 casillas y sus criterios, las pruebas de cierre por fase y los artefactos asociados. La matriz enumera cada requisito y la evidencia inspeccionada. Se cotejaron los hashes de las 395 pruebas nativas, las migraciones vacías y los controles locales de dependencias, contratos, lint/build y frontend. Los árboles de módulos, migraciones, core y pruebas backend coinciden con `794d185`; frontend coincide con `9362d94`. Se comprobaron todos los archivos del paquete desplegado y los assets de la interfaz contra sus manifiestos.

Las verificaciones existentes de carga completa, recuperación, estadísticas, exportaciones y reversa se reutilizan con sus alcances documentados; no se repiten ni se presentan como nuevas. Las pruebas HTTP autenticadas de activación y el perfil aceptado de ocho lectores conservan su evidencia anterior. La comprobación actual confirma supervisor, API, interfaz y worker activos, base/rol/revisión esperados y cero trabajos activos. Los controles de `main` se consultaron por API en modo de lectura: backend/frontend obligatorios y actualizados, aplicación a administradores, sin force push ni eliminación.

## Alcance operativo conservado

El corte publicado es el **01/10/2026**, con fecha visible y fuentes pausadas. No se declara vigencia diaria. La ausencia de DIAN y la identidad histórica no reconstruida son límites aceptados, no verificaciones externas logradas. El historial registra solo cambios observados. Los incidentes anteriores y las limitaciones de carga/IPv6 permanecen documentados.

API: `http://127.0.0.1:8000`; interfaz: `http://127.0.0.1:4173`. La operación local usa el controlador documentado de inicio/estado/detención y no presupone un servicio nuevo de arranque automático. Conservar respaldos y revisar el inventario según la política aprobada; mantener las direcciones del firewall cuando cambien los hosts autorizados. Los cambios y sus commits se mantienen **en este equipo**, sin push, merge ni publicación nueva.
