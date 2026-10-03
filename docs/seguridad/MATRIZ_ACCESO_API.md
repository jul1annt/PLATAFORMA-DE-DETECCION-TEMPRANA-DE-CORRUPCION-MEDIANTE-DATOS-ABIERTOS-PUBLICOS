# Matriz de acceso de la API

Fuente: `Backend/openapi.json`, generado por FastAPI. Se actualiza y verifica con `python scripts/export_access_matrix.py`.

## Política

- Las rutas de lectura de contratos SECOP, métricas públicas y autocompletado son públicas; las escrituras y reprocesamientos administrativos requieren un bearer de una cuenta administradora activa.
- Toda la superficie `/api/analitica` es administrativa porque publica hallazgos, clasificaciones y ejecuciones sobre proveedores o contratos.
- La gestión de fuentes, historiales de sincronización, logs de procesamiento y trabajos internos requiere administrador. Las claves de fuente no se publican.
- El login es público. El registro requiere administrador; no existe alta anónima.
- La creación de exportación de datos públicos no requiere sesión, pero se limita por volumen. Estado y descarga requieren `X-Export-Token`, firmado para un trabajo y su vencimiento; el token no va en la URL.
- Las rutas rechazan parámetros de consulta desconocidos donde se valida una consulta; los formatos, rangos y límites se validan en el servidor.

## Rutas

| Método | Ruta | Acceso | Operación |
| --- | --- | --- | --- |
| GET | `/api/analitica/directas` | Administrador autenticado (Bearer; cuenta activa) | Listar proveedores con abuso de adjudicación directa |
| POST | `/api/analitica/directas/calcular` | Administrador autenticado (Bearer; cuenta activa) | Ejecutar análisis de abuso de adjudicación directa |
| GET | `/api/analitica/directas/resumen` | Administrador autenticado (Bearer; cuenta activa) | Resumen de la última ejecución de adjudicaciones directas (dashboard) |
| GET | `/api/analitica/directas/resumen/{run_id}` | Administrador autenticado (Bearer; cuenta activa) | Resumen de una ejecución específica de adjudicaciones directas |
| GET | `/api/analitica/duplicados` | Administrador autenticado (Bearer; cuenta activa) | Listar contratos duplicados detectados |
| POST | `/api/analitica/duplicados/calcular` | Administrador autenticado (Bearer; cuenta activa) | Ejecutar análisis de duplicados en período corto |
| GET | `/api/analitica/duplicados/resumen` | Administrador autenticado (Bearer; cuenta activa) | Resumen de la última ejecución de duplicados (dashboard) |
| GET | `/api/analitica/duplicados/resumen/{run_id}` | Administrador autenticado (Bearer; cuenta activa) | Resumen de una ejecución específica de duplicados |
| GET | `/api/analitica/ejecuciones/ultimas` | Administrador autenticado (Bearer; cuenta activa) | Consultar el estado de las últimas ejecuciones analíticas |
| GET | `/api/analitica/outliers` | Administrador autenticado (Bearer; cuenta activa) | Listar contratos analizados |
| POST | `/api/analitica/outliers/calcular` | Administrador autenticado (Bearer; cuenta activa) | Ejecutar análisis IQR de outliers |
| GET | `/api/analitica/outliers/resumen` | Administrador autenticado (Bearer; cuenta activa) | Resumen de la última ejecución (dashboard) |
| GET | `/api/analitica/outliers/resumen/{run_id}` | Administrador autenticado (Bearer; cuenta activa) | Resumen de una ejecución específica |
| GET | `/api/analitica/pesos` | Administrador autenticado (Bearer; cuenta activa) | Obtener pesos de anomalías |
| PUT | `/api/analitica/pesos/{tipo_anomalia}` | Administrador autenticado (Bearer; cuenta activa) | Actualizar el peso de una anomalía |
| GET | `/api/analitica/riesgo` | Administrador autenticado (Bearer; cuenta activa) | Listar proveedores con riesgo combinado |
| POST | `/api/analitica/riesgo/calcular` | Administrador autenticado (Bearer; cuenta activa) | Ejecutar cálculo de riesgo global combinado |
| GET | `/api/analitica/riesgo/resumen` | Administrador autenticado (Bearer; cuenta activa) | Resumen de la última ejecución de riesgo global |
| POST | `/api/auth/login` | Público: inicio de sesión | Login |
| POST | `/api/auth/logout` | Administrador autenticado (Bearer; cuenta activa) | Logout |
| GET | `/api/auth/me` | Administrador autenticado (Bearer; cuenta activa) | Me |
| POST | `/api/auth/register` | Administrador autenticado (Bearer; cuenta activa) | Register |
| GET | `/api/exports/{job_id}` | Capacidad HMAC en `X-Export-Token` (por trabajo y vencimiento) | Get Export Status |
| GET | `/api/exports/{job_id}/download` | Capacidad HMAC en `X-Export-Token` (por trabajo y vencimiento) | Download Export |
| GET | `/api/ingesta/fuentes/` | Administrador autenticado (Bearer; cuenta activa) | Listar Fuentes |
| POST | `/api/ingesta/fuentes/` | Administrador autenticado (Bearer; cuenta activa) | Crear Fuente |
| GET | `/api/ingesta/fuentes/comparativa` | Administrador autenticado (Bearer; cuenta activa) | Comparativa Fuentes |
| GET | `/api/ingesta/fuentes/sincronizaciones` | Administrador autenticado (Bearer; cuenta activa) | Listar Historial |
| GET | `/api/ingesta/fuentes/sincronizaciones/export/{formato}` | Administrador autenticado (Bearer; cuenta activa) | Exportar Sincronizaciones |
| GET | `/api/ingesta/fuentes/sincronizaciones/pagina` | Administrador autenticado (Bearer; cuenta activa) | Listar Historial Pagina |
| GET | `/api/ingesta/fuentes/sincronizaciones/resumen` | Administrador autenticado (Bearer; cuenta activa) | Resumen Historial |
| DELETE | `/api/ingesta/fuentes/{fuente_id}` | Administrador autenticado (Bearer; cuenta activa) | Eliminar Fuente |
| GET | `/api/ingesta/fuentes/{fuente_id}` | Administrador autenticado (Bearer; cuenta activa) | Obtener Fuente |
| PUT | `/api/ingesta/fuentes/{fuente_id}` | Administrador autenticado (Bearer; cuenta activa) | Actualizar Fuente |
| POST | `/api/ingesta/fuentes/{fuente_id}/probar` | Administrador autenticado (Bearer; cuenta activa) | Probar Conexion |
| GET | `/api/ingesta/fuentes/{fuente_id}/sincronizaciones` | Administrador autenticado (Bearer; cuenta activa) | Historial Por Fuente |
| GET | `/api/ingesta/fuentes/{fuente_id}/sincronizaciones/pagina` | Administrador autenticado (Bearer; cuenta activa) | Historial Pagina Por Fuente |
| POST | `/api/ingesta/fuentes/{fuente_id}/sincronizar` | Administrador autenticado (Bearer; cuenta activa) | Sincronizar Fuente |
| GET | `/api/jobs/resumen` | Administrador autenticado (Bearer; cuenta activa) | Get Jobs Summary |
| GET | `/api/jobs/{job_id}` | Administrador autenticado (Bearer; cuenta activa) | Get Job |
| GET | `/api/procesados/` | Público: lectura | Listar contratos procesados |
| GET | `/api/procesados/anomalias/` | Público: lectura | Listar anomalías detectadas |
| GET | `/api/procesados/autocomplete` | Público: lectura | Autocomplete |
| GET | `/api/procesados/estadisticas/campos-faltantes` | Público: lectura | Estadísticas de campos faltantes |
| GET | `/api/procesados/export/{formato}` | Público: lectura | Exportar Contratos |
| POST | `/api/procesados/export/{formato}/jobs` | Público: crea exportación acotada; descarga exige capacidad | Crear una exportación descargable |
| GET | `/api/procesados/incompletos` | Público: lectura | Listar contratos incompletos |
| GET | `/api/procesados/logs` | Administrador autenticado (Bearer; cuenta activa) | Listar historial de ejecuciones |
| GET | `/api/procesados/logs/export/{formato}` | Administrador autenticado (Bearer; cuenta activa) | Exportar Logs Procesamiento |
| GET | `/api/procesados/metricas/calidad` | Público: lectura | Métricas de calidad de datos |
| GET | `/api/procesados/metricas/campos-faltantes` | Público: lectura | Ranking de campos faltantes |
| GET | `/api/procesados/metricas/dashboard` | Público: lectura | Dashboard Metricas |
| GET | `/api/procesados/metricas/distribucion-anomalias` | Público: lectura | Distribucion Anomalias |
| GET | `/api/procesados/metricas/distribucion-riesgo` | Público: lectura | Distribucion Riesgo |
| GET | `/api/procesados/metricas/top-proveedores` | Público: lectura | Top Proveedores |
| POST | `/api/procesados/reprocesar` | Administrador autenticado (Bearer; cuenta activa) | Ejecutar pipeline de normalización |
| GET | `/api/procesados/search` | Público: lectura | Buscar contratos procesados |
| GET | `/api/procesados/sospechosos` | Público: lectura | Listar contratos sospechosos |
| GET | `/api/procesados/{id}` | Público: lectura | Detalle de contrato procesado |
