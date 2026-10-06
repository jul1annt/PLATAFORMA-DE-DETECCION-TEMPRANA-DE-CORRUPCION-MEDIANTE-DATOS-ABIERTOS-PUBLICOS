# Propuesta de criterios de aceptación para P16

Estado: **propuesta para revisión del responsable; no aprobada ni aplicada como SLA**.

Base: mediciones locales del 2026-10-05 en `RECUPERACION_ESCRITURAS_ESCALA_20261005.md`, y recuperación del cursor ante corte HTTPS en `RECUPERACION_RED_INGESTA_20261005.md`. Esta propuesta concreta la decisión pendiente del plan. Aprobar límites no elimina los requisitos de evidencia, cobertura y despliegue.

## Límites propuestos para el ensayo

| Criterio | Propuesta | Evidencia existente / falta |
| --- | --- | --- |
| Respuestas API bajo las rondas medidas de ocho clientes | 100 % de respuestas esperadas correctas; p95 de estado y búsqueda ≤1 s | 504/504 HTTP 200; p95 de 274 y 593 ms. Falta confirmar el perfil de demanda exigido en integración. |
| Reproceso forzado de contratos ya presentes | ≥9 millones evaluados con ≥10 000 cambios controlados en ≤60 min de ejecución, excluyendo pausas explícitas del observador | El tramo recuperado de 9,22 millones tomó 31,6 min; esta cifra sola no prueba el tiempo integral del criterio. No equivale a una carga inicial con millones de inserciones. |
| Lotes de 1 000 | p95 ≤1 s; ningún lote >120 s | Tramo recuperado: 0,245 s y 50,047 s. El piloto carece de latencias individuales. |
| Recursos del conjunto de procesos propios | Memoria privada muestreada ≤512 MiB, física disponible ≥2 GiB, disco libre ≥25 GiB; muestras cada 5 s | Máxima privada observada 284,8 MiB. Hay una pausa de instrumentación declarada; la suma de working sets no mide memoria física exclusiva. |
| Pérdida del backend del worker | Solo un dueño del trabajo; el siguiente intento conserva los commits y finaliza sin repetir el prefijo; máximo tres intentos ante abandonos | Evidencia PostgreSQL pequeña y de nueve millones; prueba de agotamiento de intentos. |
| Corte de red de la fuente | Máximo seis solicitudes de una página; error terminal y sanitizado al agotarse; conserva lote/cursor/ventana/watermark, siguiente trabajo completa sin duplicados | HTTPS real local con 10 001 filas. Falta evidencia del perfil conjunto que se exija bajo carga completa y red del entorno. |

Los percentiles son de rango más próximo. Los umbrales de tiempos y memoria son valores propuestos con margen sobre lo observado; no representan una promesa de producción. Los invariantes de integridad, autorización, exclusión y conservación del cursor son obligatorios aunque se modifiquen los límites de rendimiento.

## Información que debe fijar el responsable

1. Entorno de integración, hardware, volumen, índices y versión exacta del artefacto.
2. Demanda esperada: rutas, usuarios simultáneos, frecuencia y duración. Las rondas de ocho solicitudes cada 30 s no equivalen a ocho solicitudes permanentemente activas.
3. Presupuesto para una carga inicial, un reproceso con muchos cambios y el reproceso de contratos ya consumidos. Deben medirse y aceptarse por separado.
4. Fallos exigidos, duración máxima de indisponibilidad de la fuente y conducta de reanudación permitida.
5. Límites aprobados, responsable, fecha y evidencia de aceptación. Registrar cualquier hueco de instrumentación y su resolución explícita.

## Condición de cierre

Mantener P16 abierto hasta acordar el perfil y los límites, obtener la evidencia que cubra ese perfil y cotejar resultados, latencias, recursos, fallos y exclusión de workers. Una aprobación de esta propuesta no cierra P01, P10 ni P18, que requieren sus pruebas de integración y despliegue.

## Evidencia adicional de integración — 2026-10-06

El [ensayo HTTP local](CARGA_HTTP_INTEGRACION_LOCAL_20261006.md) mantuvo ocho clientes consultando continuamente cuatro rutas sobre la integración elegida en este equipo. Hubo 842/842 respuestas correctas en 122,32 s, pero la búsqueda de 2024 alcanzó p95 **1,100 s**, superior a la propuesta de 1 s para búsqueda. Calidad global tuvo p95 **6,195 s** y proveedores **1,087 s**; sus umbrales aún no están definidos. El ensayo anterior por rondas y este circuito cerrado son perfiles distintos.

El resultado no aprueba ni ajusta automáticamente los umbrales. Antes del cierre debe fijarse el perfil exigido y, si se acepta el límite de búsqueda propuesto para este tráfico continuo, optimizar y comprobar su cumplimiento. El observador inicial omitió los hijos Python reales; la repetición breve descrita en el mismo informe corrigió ese alcance y registró 856/856 respuestas correctas. Las 27 muestras incluyeron al menos diez procesos de aplicación, con máximo privado muestreado de 207,34 MiB; junto con los backends PostgreSQL visibles, 307,32 MiB. PostgreSQL sigue sin abarcar todo el clúster y no se acredita un máximo continuo. Búsqueda p95 fue 1,044 s, todavía superior a la propuesta. También faltan los escenarios conjuntos que exija el responsable para carga inicial, reproceso con cambios y fallos. La evidencia HTTP y las huellas preservadas se reutilizarán; no se debe repetir una carga completa por defecto.
