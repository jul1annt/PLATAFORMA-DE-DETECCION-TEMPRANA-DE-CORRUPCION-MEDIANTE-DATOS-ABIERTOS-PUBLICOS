# Consultas concurrentes en la integración local — 2026-10-06

Estado: **lecturas HTTP verificadas; observador de aplicación corregido; PostgreSQL medido solo en backends visibles**. Se conservan separadas la pasada inicial y la repetición que corrigió su alcance. Aporta evidencia a P16, que conserva la aceptación del perfil y la cobertura pendientes. El plan sigue en **93/101 puntos, ocho abiertos**.

## Entorno y perfil realmente ejecutados

- Integración elegida por el usuario en este equipo: API `127.0.0.1:8000`, interfaz y worker separados, versión `9362d94f9dbfbdf352ae11585a2bfd44318b11e6`. Los tres servicios estaban activos antes y después.
- PostgreSQL 15, `plataforma_integracion_local:5433`, OID 74053, rol ordinario, revisión `f4826b9d1c30`, 20 índices; corte histórico conservado de 9 249 545 registros. Fuentes inactivas y cero trabajos activos al inicio y al final.
- Windows 10 Pro 10.0.19045, Intel Core i3-9100F de cuatro núcleos y cuatro procesadores lógicos; 17 100 582 912 bytes de memoria física utilizable, aproximadamente 15,93 GiB.
- Ocho clientes HTTP en circuito cerrado: cada uno inicia su siguiente solicitud al recibir la anterior, sin pausa. Cuatro rutas alternadas con desplazamiento por cliente, GET público sin login. Lanzamientos durante 120 s; cierre de solicitudes en curso hasta **122,323 s**. Timeout de lectura: 30 s.
- Se obtuvieron referencias secuenciales antes del ensayo. Las latencias describen lecturas posteriores a esas consultas, sin simular una caché fría, tráfico externo ni latencia de Internet. No se ejecutó reproceso, carga inicial ni un fallo de worker/fuente durante este perfil.

Las rondas de ocho solicitudes de la prueba del 05/10 y ocho clientes continuamente activos generan demandas distintas. Sus resultados se conservan por separado.

## Resultado de consultas de la primera pasada

Se completaron **842/842 respuestas HTTP 200**, sin errores ni timeout, con un promedio global de **6,88 respuestas/s**. Se comparó la huella SHA-256 del JSON completo de cada respuesta con su referencia por ruta. La búsqueda de 2024 verificó además 1 670 370 coincidencias y 20 elementos; el filtro de 2099 verificó cero coincidencias y una lista vacía.

| Ruta / consulta | Correctas / total | Mediana, s | p95, s | p99, s | Máximo, s |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/api/procesados/search`, año 2024, primera página | 210/210 | 0,369 | 1,100 | 1,514 | 1,622 |
| `/api/procesados/search`, año 2099, vacío | 211/211 | 0,004 | 0,008 | 0,019 | 0,561 |
| `/api/procesados/metricas/calidad` | 213/213 | 3,021 | 6,195 | 8,635 | 9,245 |
| `/api/procesados/metricas/top-proveedores`, límite 10 | 208/208 | 0,448 | 1,087 | 1,400 | 1,711 |

Los percentiles usan rango más próximo. Las duraciones abarcan la solicitud HTTP desde el cliente hasta recibir el cuerpo, no solo el SQL. Los resultados de cuerpos estables y conteos conocidos acreditan este perfil de lectura; no prueban todas las rutas, autorización administrativa o escrituras concurrentes.

La búsqueda p95 **1,09955 s** supera el límite de 1 s de la [propuesta de aceptación](CRITERIOS_ACEPTACION_CARGA_PROPUESTA.md), que aún no está aprobada. Calidad y proveedores tampoco tienen límites aceptados. El ensayo no declara cumplimiento de un SLA ni cambia los umbrales para acomodar sus resultados.

## Datos preservados y recursos observados

Las lecturas de comprobación usaron el rol ordinario y transacciones de solo lectura. Se cotejaron OID, esquema, fuentes pausadas y ausencia de trabajos activos. Antes y después coincidieron las huellas de las primeras 2 000 filas crudas, las primeras 2 000 procesadas y el máximo ID de trabajos. El perfil no escribió filas de aplicación ni encoló trabajos, no creó una base ni repitió carga/normalización de SECOP. Estas huellas acotadas no son una comparación exhaustiva de los nueve millones de registros.

Se registraron **27 muestras** de recursos, con separación máxima de **5,018 s**. La memoria física disponible mínima observada fue **2 846 838 784 bytes**, aproximadamente **2,65 GiB**; el disco libre mínimo fue **124 923 035 648 bytes**, aproximadamente **116,34 GiB**. No se activó el resguardo de detener nuevas solicitudes por memoria disponible inferior a 2 GiB o disco libre inferior a 25 GiB.

**Límite descubierto en el control posterior:** los PIDs que guarda el supervisor para API, interfaz y worker corresponden a lanzadores del entorno virtual; cada uno tiene un proceso hijo Python del runtime dedicado. El observador midió esos lanzadores y los backends PostgreSQL visibles para la base, pero no los hijos Python. Por tanto, el máximo de memoria privada de componentes registrado corresponde **solo a lanzadores** y no demuestra el consumo de la aplicación ni el criterio propuesto de 512 MiB. Los backends de PostgreSQL tampoco incluyen el postmaster y todos sus procesos de fondo; sus working sets pueden compartir páginas. No se infiere un máximo físico exclusivo sumando esos valores.

Se corrigió este hueco en la segunda pasada descrita a continuación. La evidencia inicial se conserva y no se convierte retrospectivamente en una prueba de memoria completa. Para el perfil aceptado todavía deberá definirse el alcance PostgreSQL exigido.

## Segunda pasada: observador corregido

Se repitió exclusivamente el perfil breve de consultas para medir los procesos que faltaban. El observador enumeró recursivamente los descendientes del supervisor, incluidos los hijos Python reales y las consolas; comprobó que cada componente tenía su hijo Python y que la fecha de creación del PID era la misma antes y después de medirlo. Se siguió comprobando la identidad de los componentes del supervisor. El primer informe permanece separado.

Esta pasada completó **856/856 respuestas correctas** en **121,560 s**, sin timeout ni error, aproximadamente **7,04 respuestas/s**. Conservó referencias de cuerpos, huellas acotadas de crudos/procesados y máximo de trabajos; las fuentes y la cola siguieron inactivas y los servicios permanecieron activos.

| Ruta / consulta | Correctas / total | Mediana, s | p95, s | p99, s | Máximo, s |
| --- | ---: | ---: | ---: | ---: | ---: |
| Búsqueda de 2024 | 214/214 | 0,417 | 1,044 | 1,395 | 1,456 |
| Vacío de 2099 | 214/214 | 0,004 | 0,007 | 0,029 | 0,138 |
| Calidad global | 216/216 | 3,081 | 5,551 | 7,776 | 9,113 |
| Diez proveedores | 212/212 | 0,497 | 1,172 | 1,583 | 1,815 |

Las **27 muestras**, con separación máxima **5,076 s**, incluyeron al menos **diez procesos** del árbol de aplicación. Su máximo de memoria privada muestreada fue **217 411 584 bytes (207,34 MiB)**. El máximo conjunto, sumando el árbol de aplicación y los backends PostgreSQL visibles en cada misma muestra, fue **322 244 608 bytes (307,32 MiB)**. Ninguna lectura de memoria de esos backends resultó indisponible. El mínimo de memoria física disponible fue aproximadamente **2,67 GiB** y el de disco libre **116,34 GiB**.

Estas cifras corrigen el alcance de aplicación de la primera pasada. El total conjunto sigue excluyendo postmaster, procesos de fondo no atribuidos y el propio generador de carga; no acredita el consumo de todo el clúster ni un máximo continuo entre muestras. No se atribuye un working set exclusivo sumando páginas compartidas. Los resultados de dos minutos no demuestran estabilidad durante una carga inicial o un reproceso largo.

Ambas pasadas suman **1 698 respuestas correctas**. No se mezclan sus distribuciones para declarar una mejora: son repeticiones de un perfil piloto, sin cambios de código o índices entre ellas. La búsqueda p95 de la segunda pasada también supera la propuesta de 1 s.

## Evidencia y siguiente condición de cierre

La [evidencia inicial](CARGA_HTTP_INTEGRACION_LOCAL_20261006.json) incluye las 842 solicitudes con cliente, orden, inicio, duración, estado y comparación de cuerpo; referencias por ruta, las 27 muestras, hardware, huellas acotadas y el límite de memoria descubierto. La [evidencia del observador corregido](CARGA_HTTP_RECURSOS_INTEGRACION_LOCAL_20261006.json) conserva las otras 856 solicitudes y sus 27 muestras con el árbol de procesos, PIDs y fechas de creación comprobadas. No incluyen cuerpos de contratos ni credenciales.

P16 requiere todavía fijar demanda y umbrales, completar la instrumentación PostgreSQL que exija el perfil y obtener la combinación de lecturas, escrituras y fallos acordada. Si se acepta búsqueda p95 ≤1 s para ocho clientes continuos con esta mezcla, deberá optimizarse y comprobarse de nuevo. Los ensayos anteriores de recuperación de nueve millones y corte HTTPS se reutilizan dentro de su alcance; no acreditan por sí solos esa combinación de carga desplegada.
