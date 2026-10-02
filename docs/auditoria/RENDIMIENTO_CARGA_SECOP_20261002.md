# Medición de la carga SECOP aislada

Estado: medición parcial mientras se carga el corte oficial de 9 249 545 filas. No define todavía un SLA de despliegue ni cierra P16.

Fuente: `Backend/.codex-e2e-postgres/secop_refresh_20261001_backfill.log`. El runner confirma 100 000 filas y un cursor en la misma transacción de cada trabajo parcial. Los índices secundarios de `raw_secop` están diferidos y se reconstruirán al finalizar. El destino es exclusivamente `plataforma_secop_refresh_20261001_test` en el clúster de prueba `:5433`.

## Corte de medición

En los primeros 54 lotes se confirmaron 5 400 000 filas en 12 697,1 segundos: promedio global **425,3 filas/s**. La mediana de duración de lote fue **202,6 s**; el percentil 95 empírico, **555,2 s**. Los primeros diez lotes promediaron **159,9 s** y los últimos diez del corte **243,8 s**. El peor lote fue el 27, con **767,4 s**; los lotes 26, 28, 39 y 40 también excedieron 475 s. El mínimo de espacio libre informado por el runner hasta ese corte fue **121,1 GiB**, por encima de su umbral de parada de 40 GiB.

La duración de cada lote se calculó restando `elapsed_s` del lote previo. La cifra incluye solicitudes de red, serialización, escritura en PostgreSQL y posibles esperas; no identifica por sí sola cuál de esos componentes produjo cada pico. Las cifras son de esta máquina y esta fuente, no de la infraestructura desplegada.

## Consulta de estado durante la importación

Con la importación activa, 40 peticiones a `GET /api/jobs/resumen` desde ocho clientes concurrentes terminaron **40/40 con HTTP 200**. Tras un calentamiento de 556 ms, la mediana fue **30,42 ms**, el percentil 95 empírico **92,08 ms** y el máximo **103,88 ms**. El artefacto de medición está en `Backend/.codex-e2e-postgres/jobs_api_during_20261001_load.json`. Se usó `FastAPI TestClient` en el mismo proceso y se sustituyó únicamente la dependencia de administrador; la ruta y PostgreSQL aislado fueron reales. Esta medida demuestra que esa consulta corta sigue respondiendo durante la carga, pero omite red, proxy, TLS y la autenticación del despliegue.

## Ajuste temporal y siguiente comparación

Antes del ajuste, PostgreSQL informó `max_wal_size=1GB`, `checkpoint_timeout=5min`, `shared_buffers=128MB` y `synchronous_commit=on`; `pg_stat_bgwriter` registró 54 checkpoints temporizados y cinco solicitados desde el inicio de sus estadísticas. El 2026-10-02 se subió solo en el clúster aislado `:5433` a 16GB y 60min, tras verificar el directorio del clon y más de 121 GiB libres. Los valores previos y el estado de restauración están en `Backend/.codex-e2e-postgres/clone_wal_tuning_20261001.json`. La comparación posterior debe usar al menos diez lotes después del cambio y señalar cualquier variación de carga externa; el vigilante final restituirá los valores originales tras el respaldo/restauración.

En la lectura posterior a aproximadamente veinte minutos de carga, los contadores seguían en 54 checkpoints temporizados y cinco solicitados, y la sesión nueva confirmó 16GB/1h. El intervalo sin nuevos checkpoints es consistente con el ajuste; no prueba todavía una mejora de latencia porque la fuente de red y otras cargas varían.

Para cerrar P16 aún faltan latencias de las consultas costosas de la API bajo carga concurrente del universo completo, picos de memoria/disco y una recuperación controlada de fallo de red o base junto con exclusión de trabajos entre workers. Las pruebas funcionales existentes ya cubren exclusión y recuperación en PostgreSQL pequeño; no se extrapolan como medición de escala.
