# Aceptación de la base del motor y de sus pesos

Fecha: 20/10/2026. Alcance: implementación local para desarrollar después, conforme a la precisión del usuario. Esta aceptación corresponde a la **base de ingeniería y evaluación descriptiva**. La aprobación predictiva y la publicación de los dos modelos conservan los requisitos del plan original.

## Decisión sobre los pesos

| Uso | Pesos | Interpretación |
| --- | --- | --- |
| Resultados históricos por proveedor | OUTLIER 1; DUPLICADO_CORTO 1,5; ABUSO_DIRECTO 2 | Configuración manual conservada para reproducir el legado; no calibrada |
| Referencia nueva por operación y etapa | Importe atípico 1; competencia 1; concentración/reiteración 1 | Conteo de familias confirmadas, con cobertura separada; no calibrado |

Cada familia aporta como máximo uno. Directas y reiteración dentro de la misma familia no suman dos veces. Convocatoria solo admite la familia de importe; adjudicación puede admitir las tres. Un campo ausente no se convierte en cero: se conservan `DETECTADA`, `SIN_SENAL`, `NO_EVALUABLE` y `NO_APLICA`, el detalle de indicadores y los motivos de abstención. Un conteo completo de familias no certifica que todos sus indicadores hayan sido observados: una condición positiva puede determinar una familia OR.

La igualdad de pesos es una referencia transparente sin evidencia para preferir una familia. No representa importancia causal, probabilidad de corrupción, porcentajes ni umbrales bajo/medio/alto. El contexto anual no añade otra familia. Política vigente: [v7](POLITICA_PESOS_BASE_V7.json).

## Matriz de aceptación del entregable inmediato

| Requisito | Implementación y comprobación | Resultado y límite |
| --- | --- | --- |
| Separar responsabilidades | Dominio, reglas, variables, materialización, entrenamiento, inferencia, persistencia y presentación en módulos propios; [arquitectura](MOTOR_RIESGO.md) | Base implementada; solicitudes ciudadanas leen resultados persistidos |
| Separar dependencias | Locks propios, intérpretes efectivos distintos de la API, entrenamiento con sklearn y sin SQLAlchemy/FastAPI; inferencia sin esos tres paquetes | Comprobado localmente el 20/10; no se añaden bibliotecas de entrenamiento a la API |
| Documentar indicadores y decisiones | `catalog.py`, política v7 y metodología pública candidata `/api/riesgo/metodologia` | Fórmulas, etapas, requisitos y límites; HTTP sin autenticación ni conexión de entrenamiento |
| Corregir comparabilidad de importes | Grupos categoría/modalidad/periodo, mínimo 30 unidades independientes e IQR positivo; [cohorte completa](REGLAS_CORREGIDAS_CORTE_2017_20261019.md) | 1.698 filas, 1.392 comparables, 50 señales; 306 no evaluables. Descriptivo del corte, sin afirmar sobreprecio |
| Ventanas reales e identidades | Procesos distintos, exclusión completa del proceso objetivo, fechas y ambigüedad por indicador; [integración SQL](INTEGRACION_SQL_VENTANAS_20261019.md) | Referencia y materialización contrastadas; 13 proyecciones reales; cobertura limitada a claves locales verificadas |
| Importes y lotes reproducibles | Decimal, monedas separadas, límites de recursos, bloqueo del lote, hashes y código congelado; [validación](IMPORTES_Y_LOTES_BASE_20261019.md) | Sin moneda no se suman importes; completar un lote no demuestra cobertura nacional |
| Composición por operación | [Evaluación conjunta](COMPOSICION_FAMILIAS_BASE_20261019.md) y política de cobertura | Conserva 1.698 objetivos y admite 13 historias; cero conteos completos por competencia desconocida. No traslada puntajes de proveedor a contratos |
| Semántica de competencia | [Auditoría documental y local](SEMANTICA_COMPETENCIA_SECOP_20261020.md) de 2.536 filas | Respuestas, invitaciones e interés quedan como contexto; oferentes reales no habilitados automáticamente |
| Contexto anual con denominador válido | [Referencia y SQL](CONTEXTO_ANUAL_BASE_20261020.md) sobre 1.478 filas reales | Fechas y calidad contrastadas; cobertura insuficiente: razón ausente. No se calcula sobre el subconjunto conocido, ni se presenta como HHI |
| Evaluar pesos existentes | [Evaluación inicial](BASE_MOTOR_Y_PESOS_20261019.md), [normalización y estabilidad](NORMALIZACION_Y_ESTABILIDAD_BASE_20261019.md) y [estratos](ESTRATIFICACION_BASE_METODOLOGIA_20261019.md) | Coherencia aritmética y sensibilidad comprobadas; censo de 31.731 resultados revela dominancia de escala IQR. No selecciona pesos óptimos ni demuestra detección real |
| Preparar validación futura | Particiones temporales, expedientes relacionados, positivos/sin etiqueta, recuperación y lift, bootstrap por expediente, proveedores no vistos | Implementado y probado con fixtures; faltan datos reales admisibles para evaluar modelos |
| Versionar y reproducir | Manifiestos, hashes de datos/código/locks, referencias congeladas y CLIs desconectados | Evidencias anteriores identifican sus versiones; no se atribuyen ensayos antiguos a código posterior |
| Preparar ejecución y publicación controladas | Pipeline durable, captura por generación, activación atómica, reversa, controles administrativos y [paquete aislado](PAQUETE_AISLADO_20261019.md) | Infraestructura ensayada; activación denegada sin modelos aprobados. No desplegada sobre la publicación histórica |
| Conservar operación local | Lectura original del 20/10: PostgreSQL 15.19, OID 24577, revisión `3c19a8f7e2d0`, fuentes activas 0 y trabajos no terminales 0 | Corte 01/10/2026 y pesos originales conservados; API e interfaz responden 200. No se tocaron respaldos ni se asignaron identidades al legado |

## Evidencia final y alcance de pruebas

El recibo [VALIDACION_BASE_FINAL_20261020.json](VALIDACION_BASE_FINAL_20261020.json) registra la batería final, hashes de código y política, inventario reproducido y comprobaciones del entorno. Los archivos privados de adquisición y ejecución permanecen en `Backend/.codex-analytics-postgres/`; el recibo público contiene agregados y hashes, sin credenciales.

La metodología candidata expone los pesos desde las definiciones reales de familias, su aplicabilidad por etapa y los límites de publicación. Cuatro pruebas nuevas comprueban esa correspondencia, aislamiento de la configuración devuelta, semántica de denominadores/oferentes y acceso HTTP público. La interfaz tiene 11 pruebas aprobadas. La compilación y la batería final se documentan con su resultado efectivo en el recibo.

Los ensayos de volumen y del paquete aislado anteriores siguen siendo evidencia de sus versiones. **No acreditan rendimiento a volumen completo de los nuevos materializadores anuales ni de futuros modelos reales.** Esa medición se exigirá antes de activar una nueva publicación.

## Continuación posterior condicionada

1. El inventario reproducido contiene **14 candidatos y cero casos admisibles**. Faltan decisiones originales, firmeza y/o vínculos exactos y evidencia temporal, según cada exclusión. No se entrenaron modelos reales.
2. Obtener información pública suficiente sobre ofertas por lote, historia temporal y cobertura; no reinterpretar respuestas como ofertas ni completar identidades inferidas.
3. Entrenar y evaluar por separado convocatoria/adjudicación con corpus suficiente, bloques cronológicos independientes y comparación con reglas. Conservar los criterios de recuperación al 5 % e intervalo por expediente exigidos por el plan.
4. Solo tras aprobación: medir recursos del candidato real a volumen completo, validar operación/recuperación, activar localmente modelos y publicación con reversa. La sincronización diaria nueva permanece desactivada.

La base permite continuar estas tareas sin presentar las anomalías como corrupción comprobada. No se contactó a terceros y no se autorizan contactos. El [plan predictivo ampliado](AUDITORIA_PLAN_MOTOR_20261016.md) conserva sus pendientes; el plan anterior del proyecto mantiene su cierre independiente.
