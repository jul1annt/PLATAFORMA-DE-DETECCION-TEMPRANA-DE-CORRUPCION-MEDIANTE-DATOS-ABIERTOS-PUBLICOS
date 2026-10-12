# Preparar conexiones PostgreSQL antes de atender tráfico local

Estado: **implementado y probado en el candidato local `794d185`; activación en la base publicada pendiente**. [Evidencia y límites](../auditoria/VALIDACION_LOCAL_PENDIENTES_20261011.md).

## Configuración comprobada

```dotenv
DB_POOL_PREWARM=10
DB_POOL_MAX_OVERFLOW=0
DB_CONNECT_TIMEOUT_SECONDS=60
SEARCH_QUERY_PARALLEL_WORKERS=0
PROVIDER_QUERY_PARALLEL_WORKERS=0
```

El pool base tiene diez conexiones. La API prepara diez sesiones independientes antes de completar su startup; hasta entonces no declara disponibilidad. Cada sesión comprueba base, rol, puerto, dirección loopback y ausencia de privilegios de superusuario, creación de bases/roles o replicación. Las consultas de preparación son de solo lectura, con espera SQL local de cinco segundos; al devolver las conexiones, se revierte la transacción y se restauran sus ajustes. La dirección usa `host(inet_server_addr())` para separar la máscara de red de la dirección.

La configuración de preparación exige `DB_HOST` local, cero overflow y espera de conexión de hasta 60 s. Un fallo aborta la barrera de preparación y el startup, sin incluir credenciales en el error. El supervisor local permite 180 s para confirmar disponibilidad cuando se activa preparación, frente a sus 90 s habituales. El worker dedicado mantiene su propio pool y no ejecuta el startup de FastAPI.

La preparación está desactivada por defecto (`0`), y el overflow sigue en `20` al omitirlo. La espera de conexión predeterminada es ahora 60 s; no impone un tiempo máximo a todas las consultas. Antes de activar, comprobar capacidad de PostgreSQL para las conexiones de API, worker y demás aplicaciones; no deducir capacidad de este piloto para más clientes o destinos remotos.

## Comprobaciones realizadas

- **395 pruebas PostgreSQL pasaron en 36,34 s**. La base sintética pequeña se reutilizó después de corregir la conversión de la dirección; las migraciones no se repitieron en el corte completo. El caso anterior de 395 pruebas y fallo posterior de preparación se conserva separado.
- Preparación nativa de diez conexiones: **0,264 s**, slots distintos, rol ordinario y ajustes de transacción restaurados.
- Paquete de **200 archivos y 187 fuentes Python compiladas**, locks iguales, OpenAPI/matriz iguales con conexiones prohibidas durante esas importaciones. El frontend y los tipos API no cambiaron.
- En la copia completa existente, ocho lectores continuos durante 120 s produjeron **9.884/9.884 respuestas correctas**, cero errores y cero conexiones nuevas después de preparar el pool. Búsqueda p95 0,269 s; calidad 0,0048 s; proveedores 0,265 s. Las huellas acotadas y el resumen antes/después coincidieron; no se escribió ni se reprocesó contrato.

Las 25 capturas incluyen generador/API/hijos y el clúster :5433. Máximo privado en una misma captura: 235.188.224 bytes; mínimo físico: 4.965.335.040 bytes; intervalo máximo: 5,156 s. Se excluye :5432 aunque comparte el equipo; son muestras, no picos continuos.

La prueba nueva verifica la mitigación en ese perfil de lectura. No reproduce otra transformación inicial ni un nuevo ensayo conjunto largo con fallos. Los repositorios, worker, ingesta y migraciones son idénticos al candidato `ec9b5d2` que completó el recorrido y las recuperaciones; esa evidencia se reutiliza con su alcance explícito. Los timeouts anteriores permanecen registrados y su causa interna no se considera resuelta por tres conexiones rápidas posteriores.

## Activación local

Seguir [despliegue y reversa](../auditoria/GUIA_DESPLIEGUE_Y_REVERSA.md): aceptación del perfil, respaldo/checkpoint actuales, destino/OID/rol comprobados, ausencia de escritores, migraciones compatibles, backend/worker de la misma revisión y comprobaciones posteriores. Aplicar los ajustes solo al runtime elegido y registrar sus hashes. No volver a cargar el corte para activar el resumen o la preparación del pool.
