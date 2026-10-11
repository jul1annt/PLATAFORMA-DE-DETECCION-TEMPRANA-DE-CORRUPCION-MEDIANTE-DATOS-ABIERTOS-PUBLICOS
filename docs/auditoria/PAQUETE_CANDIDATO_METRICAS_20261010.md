# Paquete local del candidato de métricas — 2026-10-10

Estado: **preparado e inactivo**. El plan permanece en **95/101 (94,1 %), seis pendientes**.

**Decisión posterior, 2026-10-11:** el usuario indicó «Mantener cambio en este equipo». La autorización GitHub dejó de estar pendiente: los cambios se conservan localmente. Las referencias de este informe y de su JSON a esa autorización describen la preparación del 10/10; se preservan como evidencia histórica. La decisión no acredita CI ni autoriza activar el candidato; los demás requisitos de despliegue y cierre siguen pendientes.

## Artefacto identificado

| Elemento | Resultado comprobado |
| --- | --- |
| Backend de origen | `6a5cb4697a140dd68a6d030b10eb6e1070f5f920` |
| Árbol Git del backend | `12be9663c762830ed62a64308deb96af206e41f7` |
| Archivo | 368 640 bytes, 196 archivos de Backend |
| SHA-256 del archivo | `308b96841dd6afcf7d4f54b40f09a812b5c1dee326d41d9127eef8c79d941da2` |
| Fuentes Python | 183 compiladas sin ejecutar sus cuerpos |
| Runtime | Lock idéntico; `pip check` aprobado; versiones de `pip freeze` iguales al inventario original |
| Importación | 63 rutas; conexiones a bases de datos prohibidas durante la comprobación |
| Frontend reutilizable | Fuente `9362d94`, árbol Git idéntico y bundle activo validado por el control local |
| Revisión objetivo | `2ab7c4e8d910`; actual conservada `f4826b9d1c30` |
| Preparación final | 2026-10-10 17:54:13 UTC, 12:54 en Bogotá |

El candidato se conserva en `Backend/.codex-integration-postgres/releases/6a5cb4697a14`. Incluye solo archivos rastreados del backend. La extracción rechaza rutas fuera del directorio, tipos de entrada no admitidos y valores secretos activos. El manifiesto privado conserva las huellas de cada archivo y los vínculos con las pruebas anteriores.

## Diferencias comprobadas y continuación

La primera preparación se detuvo antes de verificar el runtime: las huellas originales de las seis fuentes probadas diferían de las del archivo Git. Cada fuente del directorio de trabajo seguía coincidiendo exactamente con su huella registrada en la suite final de **333 pruebas en 44,18 s**. La comparación de bytes demostró que la única diferencia entre fuente probada y paquete era CRLF/LF. Se registran la huella probada, la del paquete y la normalizada; no se atribuye a esas pruebas una igualdad de bytes inexistente.

Antes de continuar se cotejaron byte a byte los 196 archivos extraídos con el archivo conservado. Una segunda detención identificó el uso de `pip list` frente al `pip freeze` empleado al crear el inventario original: solo añadía el instalador `pip 24.2`, sin paquetes faltantes ni cambios de versiones. Se comparó con el mismo método original y pasó. Se conservó el registro de dependencias, sin reinstalarlas ni modificar el runtime compartido.

La importación usó configuración sintética y un bloqueo de conexiones SQLAlchemy. No inició un ensayo HTTP ni probó el rendimiento sobre el corte completo. Las 333 pruebas son evidencia nativa previa de ese código con equivalencia CRLF/LF demostrada; esta preparación no es una nueva suite ni una instalación limpia.

## Configuración activa y publicación

Durante la preparación final conservaron sus huellas `release.json`, `runtime.json`, `runtime.env`, `provision.json` y `frontend-build.json`. Los procesos identificados de API, interfaz y worker seguían vivos. El backend/worker aplicado permanece en `915e863`, con frontend `9362d94`; el paquete está inactivo y su manifiesto indica `activation_allowed=false`.

Una consulta remota **solo GET**, del 2026-10-10 a las 17:42:29 UTC, confirmó que el [PR de borrador #1](https://github.com/jul1annt/PLATAFORMA-DE-DETECCION-TEMPRANA-DE-CORRUPCION-MEDIANTE-DATOS-ABIERTOS-PUBLICOS/pull/1) sigue abierto, en `1cdb719dacb7a2e630e91461d13aaf902a09eafb`, rama `plan/accion-20261002`. No devolvió ejecuciones CI para `6a5cb4697a140dd68a6d030b10eb6e1070f5f920`. Las cuatro mejoras locales posteriores permanecen sin publicar. El push sigue sujeto a la autorización del destino solicitada tras el rechazo automático; esta consulta no publicó ni modificó el PR.

## Requisitos pendientes de activación

- Autorización explícita del destino GitHub y CI exitoso del código identificado en el artefacto que se vaya a desplegar.
- Preparación y ensayo de migraciones compatibles, respaldo y recuperación según la [guía de despliegue](GUIA_DESPLIEGUE_Y_REVERSA.md).
- Inicialización única y cotejo independiente del resumen sobre el corte completo; medición de lecturas, escrituras y contención conforme a la [guía del resumen](../operacion/RESUMEN_METRICAS_TRANSACCIONAL.md).
- Perfil HTTP conjunto con reproceso, fallos y recuperación; aprobación de sus límites. El coste de escritura medido y los límites del ensayo pequeño permanecen en el [informe del resumen](RESUMEN_METRICAS_TRANSACCIONAL_20261010.md).

La preparación no cierra P16 ni modifica las dependencias de P01, P05, P06, P12 o P15. No hubo migración, reingesta, normalización ni eliminación adicional de datos en esta etapa.

[Evidencia estructurada sanitizada](PAQUETE_CANDIDATO_METRICAS_20261010.json): manifiesto, 196 huellas, equivalencia de las seis fuentes, runtime, importación y lectura remota. Se omitieron valores de configuración y credenciales; la salida se cotejó contra los secretos activos y patrones JWT.
