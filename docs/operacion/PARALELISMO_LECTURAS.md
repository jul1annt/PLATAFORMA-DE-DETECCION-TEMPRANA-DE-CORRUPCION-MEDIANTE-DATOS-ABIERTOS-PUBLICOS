# Paralelismo opcional de búsquedas y proveedores

Estado actual: **preparado localmente, desactivado en el runtime publicado**. Las [mediciones SQL](../auditoria/PARALELISMO_LECTURAS_20261010.md) no acreditan mejora de calidad ni cumplimiento HTTP.

El artefacto que incorpore `core/read_database.py` admite dos variables opcionales:

| Variable | Ruta afectada | Valor omitido |
| --- | --- | --- |
| `SEARCH_QUERY_PARALLEL_WORKERS` | GET `/api/procesados/search` | Usa la configuración PostgreSQL vigente |
| `PROVIDER_QUERY_PARALLEL_WORKERS` | GET `/api/procesados/metricas/top-proveedores` | Usa la configuración PostgreSQL vigente |

Los valores válidos son enteros entre 0 y 1024. Cero impide usar workers paralelos para esa transacción. Un límite no garantiza que PostgreSQL lance ese número: depende del plan y de los recursos disponibles. No definir valores elevados sin medir su costo conjunto.

La dependencia de cada ruta recibe la misma sesión administrada por `get_db` y ejecuta `set_config('max_parallel_workers_per_gather', valor, true)`. El tercer argumento limita la duración a la transacción. Su commit/rollback o el cierre de la sesión restaura el valor, incluidos errores SQL; el pool no transmite el ajuste a la siguiente petición. Las rutas de métricas, exportaciones y el worker conservan su configuración habitual. SQLite no recibe comandos PostgreSQL.

## Activación y reversa

1. Publicar/verificar el CI del artefacto compatible y preparar su despliegue conforme a [la guía de integración](INTEGRACION_LOCAL.md). La autorización del destino GitHub sigue pendiente; las opciones aún no están disponibles en el backend aplicado `915e863`.
2. Registrar las variables actuales y el perfil de carga. Definir únicamente las opciones que se vayan a comparar en el archivo privado de configuración del nuevo artefacto; no editar `postgresql.conf` ni aplicar `ALTER SYSTEM` para este ajuste.
3. Reiniciar la API con la versión/configuración identificadas. Medir el mismo perfil HTTP completo, incluyendo calidad y las otras rutas, cuerpos correctos, recursos y conservación de datos/cola. En SQL, cero en búsqueda/proveedores favoreció esas rutas y empeoró calidad; no extrapolar aceptación ni activar automáticamente ambos valores.
4. Para revertir, retirar las opciones y reiniciar la API. Verificar versión, respuestas, fuentes pausadas y cola. No hace falta migración, downgrade o modificación de índices por estas variables.

Las variables de entorno no son una interfaz pública: no se aceptan como parámetros HTTP. Se conserva el contrato OpenAPI y la matriz de acceso.
