# Motor analítico por etapas

## Mejora posterior: política v8 — 20/10/2026

La [priorización con cobertura y sensibilidad de pesos](MEJORA_MOTOR_Y_PESOS_V8_20261020.md) añade límites de posición y rutas de revisión al motor candidato, manteniendo la referencia central 1/1/1. Comprueba todos los pesos entre 0,80 y 1,20 y conserva la contribución desconocida como intervalo. La [política vigente v8](POLITICA_PESOS_BASE_V8.json) sucede a v7; las evidencias de la entrega anterior describen sus versiones. La metodología candidata y la composición por operación ya incorporan esta mejora. No se alteran pesos ni resultados publicados.

## Base para desarrollo posterior — 20/10/2026

El entregable inmediato acordado es una base sólida del motor y sus pesos para evolucionar después. La [aceptación de la base](ACEPTACION_BASE_MOTOR_20261020.md) reúne requisitos, evidencias y límites; la [política vigente v7](POLITICA_PESOS_BASE_V7.json) conserva los coeficientes históricos 1 / 1,5 / 2 y fija una referencia no calibrada de un punto por familia, con cobertura por operación y etapa.

| Área | Estado actual y evidencia |
| --- | --- |
| Evaluación de pesos | [Evaluación inicial](BASE_MOTOR_Y_PESOS_20261019.md), [censo y normalización](NORMALIZACION_Y_ESTABILIDAD_BASE_20261019.md), [estratos contractuales](ESTRATIFICACION_BASE_METODOLOGIA_20261019.md). Se evalúan escalas y estabilidad; no capacidad predictiva ni pesos óptimos |
| IQR corregido | [Cohorte completa](REGLAS_CORREGIDAS_CORTE_2017_20261019.md): 1.698 filas, 1.392 comparables, 50 señales y 306 no evaluables |
| Ventanas y lotes | [Integración SQL](INTEGRACION_SQL_VENTANAS_20261019.md), [importes y ejecución reproducible](IMPORTES_Y_LOTES_BASE_20261019.md); 13 proyecciones reales verificadas. Importes sin moneda no se agregan |
| Composición | [Familias por operación](COMPOSICION_FAMILIAS_BASE_20261019.md): 1.698 objetivos, 13 historias admitidas, cero conteos completos por competencia desconocida |
| Competencia | [Semántica auditada](SEMANTICA_COMPETENCIA_SECOP_20261020.md): 2.536 filas; respuestas e invitaciones no acreditan oferentes reales; captura automática deshabilitada |
| Participación anual | [Referencia y SQL](CONTEXTO_ANUAL_BASE_20261020.md): 1.478 filas reales, denominador insuficiente; razón ausente, sin puntuar sobre el subconjunto conocido |
| Metodología pública candidata | Catálogo alineado con reglas, pesos reales de familias, abstenciones y límites. No habilita un índice ciudadano ni altera la publicación histórica |

Las referencias anteriores v1–v6 conservan la evolución de decisiones; no sustituyen el estado v7. Las mediciones de volumen previas corresponden a sus versiones y deberán repetirse para un candidato predictivo antes de activarlo. La evaluación del corte actual es descriptiva y no se admite automáticamente como información histórica para entrenar.

El inventario reproducido el 20/10 contiene 14 candidatos y **cero aptos**; el [recibo final](VALIDACION_BASE_FINAL_20261020.json) identifica sus hashes. Buscar nuevas sentencias y entrenar no son condiciones para disponer de esta base de desarrollo; siguen siendo requisitos para aprobar los modelos futuros. Está prohibido contactar a terceros.

## Estado de la entrega

Implementación local candidata. La base publicada, el corte del 01/10/2026, las fuentes pausadas, el legado y sus respaldos se conservan. El plan anterior sigue cerrado con su alcance original.

El índice nuevo y la sincronización diaria **no están activados**: hay 14 candidatos y cero casos utilizables para entrenamiento. El inventario y sus exclusiones se reprodujeron el 20/10; la [revisión 16](INVENTARIO_CASOS_REVISION16_20261019.json) conserva la investigación previa. No hay modelos judiciales reales aprobados. Las revisiones históricas son antecedentes y no prueban suficiencia del corpus.

Las pruebas con datos sintéticos acreditan funcionamiento del software. No acreditan detección de corrupción real, precisión predictiva ni aprobación de modelos operativos.

La [preparación de evidencias por etapa](EVIDENCIAS_ETAPA_RUTA_DEL_SOL_20261018.md) recuperó dos documentos de ANI y comprobó límites concretos de disponibilidad, versiones, fechas y significado del importe. Se mantienen como investigación: no se registran como observaciones históricas completas. Las herramientas documentales tienen 28 pruebas correctas y conservan sus dependencias separadas de API y modelos.

## Cómo se determina una alerta

La alerta es una señal para revisar una operación y su expediente. No es una declaración de culpabilidad. La decisión judicial se utiliza como referencia de entrenamiento únicamente cuando identifica hechos y operaciones concretas, y existe evidencia de firmeza.

Cada operación requiere un vínculo judicial revisado: hash de la sentencia, resultado `CONDENA_CORRUPCION`, localizador de hechos y localizador de la parte resolutiva. Una sentencia puede condenar por unos hechos y anular otros; los contratos mencionados en cargos anulados, absoluciones o investigaciones no se convierten en positivos. La [revisión de SEP077-2023](HALLAZGOS_JUDICIALES_REV5_20261016.md) motivó esta comprobación. Las referencias de contrato, portafolio, proceso, aviso y adjudicación se mantienen distintas; una coincidencia de proceso no permite inventar una adjudicación o sustituir el ID de una fila histórica.

La metodología combina:

- [Fazekas, Tóth y King](https://doi.org/10.1007/s10610-016-9308-z): relaciones entre restricciones de competencia, adjudicaciones recurrentes e índices de riesgo.
- [Fedesarrollo/IMCO, Colombia](https://imco.org.mx/wp-content/uploads/2019/07/FEDESARROLLO_CPBD.pdf): indicadores de competencia, transparencia y anomalías adaptados al sistema colombiano. Sus umbrales no se trasladan automáticamente.
- [Open Contracting, guía de 2024](https://www.open-contracting.org/resources/red-flags-in-public-procurement-a-guide-to-using-data-to-detect-and-mitigate-risks/): requisitos de datos, unidad de análisis, indicadores y revisión contextual.
- [Estudio sobre aprendizaje PU en contratación](https://arxiv.org/abs/2102.05523): uso de positivos y observaciones sin etiqueta. Ausencia de condena conocida no equivale a un negativo verificado.

El catálogo implementado está en `Backend/modules/motor_riesgo/catalog.py` y se publica en `/api/riesgo/metodologia`. Incluye fórmulas, fuentes, requisitos y límites. La reiteración en 30 días y las directas en 90 días son ventanas operativas del proyecto; no son umbrales legales que demuestren fraccionamiento o abuso.

El [diccionario SECOP revisado](SEMANTICA_SECOP_20261016.json) descarta usar respuestas como número de oferentes: algunas incluyen intervenciones de la entidad. Tampoco se usa automáticamente la recepción de respuestas como fecha definitiva de cierre. La duración guardada corresponde al proceso de compra y solo se convierte cuando su unidad expresa días.

## Responsabilidades y dependencias

| Componente | Responsabilidad | Dependencias |
| --- | --- | --- |
| `modules/motor_riesgo/domain.py`, `rules.py`, `catalog.py` | Contratos, elegibilidad, reglas y metodología | Biblioteca estándar |
| `analytics_ml/corpus.py`, `evidence.py`, `evaluation.py` | Inventario, evidencia física revisada, identidad, particiones y métricas | Biblioteca estándar |
| `analytics_ml/training.py` | Ensambles PU de regresión logística | Entorno de entrenamiento, lock propio |
| `analytics_ml/inference.py` | Transformación e inferencia portable con explicación | Biblioteca estándar, entorno separado |
| `modules/motor_riesgo/service.py`, `pipeline.py` | Persistencia, trabajos, publicación y recuperación | Dependencias existentes del backend |
| `controller.py`, interfaz React | Autorización y lectura de resultados persistidos | Sin entrenamiento dentro de solicitudes HTTP |

Los entornos de entrenamiento e inferencia están separados. Entrenamiento usa CPU con un solo hilo por biblioteca. El índice se calcula con el margen medio del ensamble, compilado a un vector lineal, y se transforma en un percentil con una referencia congelada por versión. No se cargan pickle/joblib ni objetos Python desde artefactos externos: el intercambio es JSON con hashes y validación de dimensiones.

El lanzador valida la ubicación del registro antes de ejecutar, retira las variables `DB_`, `SECRET_` y `ENCRYPTION_` del entorno y fija salida UTF-8. En Windows inicia suspendido y asigna el comando a un Job Object privado antes de reanudarlo. El SO cierra sus descendientes si muere el propietario; el plazo máximo también termina ese árbol. En POSIX utiliza una sesión privada, sin atribuirle esa garantía de muerte del propietario. Un cierre no confirmado se registra como fallo. El [control de procesos](CONTROL_PROCESOS.md) documenta las pruebas reales de plazo, salida abrupta del supervisor y recuperación del mismo trabajo durable; el [ensayo HTTP del paquete aislado](PAQUETE_AISLADO_20261019.md) completó dos ciclos; el despliegue con modelos reales aprobados sigue pendiente.

Cada ejecución conserva un registro `.process.execution.json` con límite de tiempo, hilos, estado y hashes del ejecutable del entorno virtual y del lanzador. Es procedencia de ejecución, separada del manifiesto predictivo: la aprobación del modelo no depende del código de orquestación de la API. No se añaden dependencias de entrenamiento a la API.

Las dependencias de la API permanecen en sus archivos originales. El lock de entrenamiento está en `Backend/analytics_ml/requirements-training.lock`. Inferencia no necesita NumPy ni scikit-learn.

Cada entrenamiento conserva las versiones reales de Python, scikit-learn, NumPy, SciPy, joblib y threadpoolctl, además de hashes del lock y del código de variables, reglas, evidencias, entrenamiento y evaluación. El modelo enlaza ese manifiesto y la revisión de evidencias por hash. Activación e inicio Windows usan la misma política de aprobación.

La [auditoría de particiones temporales](PARTICIONES_TEMPORALES_20261019.md) registra tamaños, exclusiones, motivos y etiquetas tratadas como desconocidas por fecha. El modelo enlaza `split_audit` mediante hash; aprobación exige que las filas usadas más las excluidas correspondan al conjunto verificado. No se confunden etiquetas futuras reclasificadas con operaciones excluidas.

El artefacto también vincula los bytes de `inference.py`, `runtime.py` y el dominio compartido. La inferencia nueva rechaza una implementación diferente, aunque alguien conserve manualmente el nombre de versión de variables. Una publicación histórica íntegra se puede restaurar sin ejecutar ese modelo antiguo.

## Registro y conjunto de casos

Los documentos originales se guardan fuera de Git, en `RISK_WORK_DIR/evidence`. El registro de cada caso conserva:

- `case_id`, autoridad, radicado, conducta, fecha de disponibilidad de la etiqueta y firmeza, revisor y grupo de expedientes relacionados.
- `judgment` y `finality`: URL oficial HTTPS, archivo local y SHA-256. Un comunicado no sustituye esos documentos.
- `judgment.kind=SENTENCIA_CONDENATORIA`; `finality.kind=CONSTANCIA_EJECUTORIA`, `PROVIDENCIA_ULTIMO_RECURSO` o `PROVIDENCIA_ACREDITA_FIRMEZA`, y `finality.judgment_sha256` enlazado a esa sentencia concreta. La ausencia de recursos contra un auto procesal no lo convierte en condena.
- Política `reviewed-finality-effect-v2`: `finality.reviewed=true`, `finality.effect=FIRMEZA_CONFIRMADA` y `finality.locator` documental no vacío. Para `PROVIDENCIA_ACREDITA_FIRMEZA` se exigen además `declared_final_at`, igual a `final_at`, y `declaration_date_locator`: la fecha del auto posterior no sustituye la ejecutoria que declara. Un aviso que abre el término de recursos, su vencimiento previsto o la ausencia de recursos contra un anuncio no prueban firmeza de la sentencia.
- `operations`: `source_id`, `source_row_id`, `process_id`, `award_id`, `lot_id` y `match=EXACTO`.
- Fecha documentada de primera investigación. Su ausencia impide utilizar el caso; la fecha de sentencia no la sustituye.

Una coincidencia de nombre, un NIT sancionado o un número de contrato sin entidad/año suficientes no constituyen una correspondencia exacta. No se propagan etiquetas a otras operaciones del mismo proveedor. La proyección de adjudicación a convocatoria exige un vínculo de etapa revisado explícitamente. Corrupción y fraude contractual se conservan diferenciados; solo `CORRUPCION` se utiliza como positivo del modelo.

Las observaciones JSONL incluyen etapa, identidad, momento de predicción y variables con `available_at` y hash. Para entrenar necesitan además `feature_evidence_id`, vinculado a una revisión administrativa preservada. Se verifican documentos físicos, hashes y coincidencia exacta con la observación revisada; fechas y valores requieren revisión humana autenticada. El [protocolo de evidencias](EVIDENCIAS_VARIABLES.md) detalla formato y límites.

Se excluyen información futura, nombres y documentos judiciales como predictores, y observaciones sin variables esenciales. La versión `secop-point-in-time-v3` usa la política `reviewed-stage-landmark-v1`: una captura actual se abstiene. La inferencia solo utiliza las mismas observaciones históricas revisadas que admite el entrenamiento, vinculadas a una fila y etapa exactas. Revisa sus archivos físicos, fechas y valores sin mezclarlos con datos actuales. Las revisiones en conflicto se abstienen y un corte compuesto solo por abstenciones no se publica. La equivalencia de variables está probada con fixtures sintéticas de ambas etapas; faltan documentos y observaciones reales utilizables.

Reproducir el inventario desde la raíz del repositorio, usando un nombre de salida nuevo para conservar revisiones anteriores:

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_inventory.py --cases docs/analitica/casos_candidatos.json --evidence Backend/var/risk/evidence --output inventario-nuevo.json
```

## Entrenamiento y aprobación

Configurar en el **entorno candidato**, con rutas absolutas:

```dotenv
RISK_WORK_DIR=C:/ruta/privada/risk
RISK_TRAINING_PYTHON=C:/ruta/entorno-entrenamiento/Scripts/python.exe
RISK_INFERENCE_PYTHON=C:/ruta/entorno-inferencia/Scripts/python.exe
```

Crear ambos entornos con Python 3.13, instalar entrenamiento con `pip install --require-hashes -r analytics_ml/requirements-training.lock` y conservar la versión del intérprete junto al manifiesto del despliegue. El entorno de inferencia puede crearse con `venv --without-pip`.

Rutas administrativas, todas con sesión Bearer activa:

- `POST /api/riesgo/admin/casos`: registrar expediente y su evidencia; devuelve exclusiones.
- `GET /api/riesgo/admin/inventario`: consultar inventario registrado.
- `POST /api/riesgo/admin/evidencias-variables`: registrar una revisión inmutable de variables, documentos, fechas, valores e identidad SECOP exacta.
- `GET /api/riesgo/admin/evidencias-variables`: consultar revisiones paginadas.
- `POST /api/riesgo/admin/entrenar`: indicar un archivo JSONL o JSONL gzip dentro de `RISK_WORK_DIR`. El trabajo se serializa y ejecuta fuera del proceso HTTP.
- `GET /api/riesgo/admin/modelos`: informes y versiones candidatas.
- `POST /api/riesgo/admin/preparar-base`: encolar la preparación del corte ciudadano inicial; devuelve 202 y conserva una única ejecución activa.
- `POST /api/riesgo/admin/activar`: seleccionar UUID de convocatoria y adjudicación aprobados; `daily` determina la programación.
- `POST /api/riesgo/admin/actualizar`: preparar un corte con los dos modelos aprobados.
- `POST /api/riesgo/admin/revertir/{cut_id}`: volver a un corte previamente publicado; pausa la actualización diaria.

El entrenamiento limita cada ejecución a 200.000 observaciones/512 MiB descomprimidos. Congela el contenido lógico, el archivo físico, los casos y el registro de evidencias; comprueba los insumos realmente leídos por el subproceso. Si el conjunto excede los límites, requiere una muestra estratificada y versionada; no se trunca silenciosamente. Cada etapa usa 25 regresiones, semillas fijas y selección de C entre 0,1; 1; 10 mediante ajuste. La referencia y las transformaciones se ajustan con entrenamiento, sin reentrenar sobre la reserva final.

El vocabulario categórico conserva hasta 512 categorías y 100 valores para cada una de modalidad y departamento; los demás se representan explícitamente como desconocidos. Más de 10.000 positivos exige una muestra versionada por expediente antes de entrenar. La inferencia informa valores fuera de la referencia en lugar de ocultarlos.

Se exigen al menos cinco expedientes positivos independientes en entrenamiento, ajuste y reserva después de aplicar restricciones temporales. Se miden recuperación de positivos conocidos y lift al 1 %, 5 % y 10 %, con manejo fraccional de empates. La aprobación exige intervalo del 95 % de mejora frente a reglas, al 5 %, completamente superior a cero; también debe superar el ensayo con proveedores no vistos. El bootstrap utiliza 2.000 remuestreos por expediente. Estos mínimos técnicos no garantizan suficiencia estadística ni representatividad de toda la corrupción.

## Operación diaria y conservación

Las migraciones aditivas llegan a `f67b120ce841`: tablas analíticas, contadores de origen, revisiones de evidencia, historiales ciudadanos incrementales y agregados persistidos. Se aplicaron únicamente en copias aisladas. La reversa rechaza eliminar evidencia; PostgreSQL restaura transaccionalmente el esquema, los ocho triggers de origen y los ocho ciudadanos al rechazar la operación. La reversa operativa cambia juntos los datos y resultados del corte anterior, comprueba el certificado de aprobación conservado y pausa la programación. No ejecuta un estimador obsoleto para servir resultados históricos.

El scheduler comprueba cada minuto la fecha operativa de las 03:00, `America/Bogota`, y recupera una ejecución pendiente al iniciar el worker. La cola durable evita solapamientos. La ingesta conserva su propio trabajo/cursor y la normalización reutiliza su trabajo independiente. Una actualización incompleta no activa resultados parciales.

La captura diaria recorre las identidades y campos básicos por lotes de 1.000 filas, sin preparar agregados actuales de todo el universo. Recupera las variables históricas del registro de evidencia revisada. Solo las operaciones con revisiones requieren consultar sus posibles alias, mediante el índice del proceso original; las filas todavía no normalizadas también cuentan para detectar ambigüedad. El total de la población seleccionada se cuenta durante el recorrido completo por IDs, evitando un segundo recorrido previo para contar. El llamador comprueba las revisiones transaccionales de la fuente antes y después de la captura y antes de publicar. El modo explícito `include_current_context=True` conserva los agregados actuales para diagnóstico y comparación independiente; no reconstruye el pasado.

Captura y resultados usan JSONL gzip determinista, con hashes físicos y lógicos separados. Los dos modelos se ejecutan en una sola lectura, cada uno sobre su etapa. La firma consulta dos contadores transaccionales; un bloqueo breve comprueba los cambios antes de activar juntos los dos punteros. Se requiere una reserva de 25 GiB más el presupuesto de preparación. No se eliminan cortes, respaldos ni casos automáticamente.

La [medición de captura en 9.249.545 registros](RENDIMIENTO_CAPTURA_20261016.json) obtuvo 602,65 s de preparación y 0,09–0,16 s por lote de 1.000 en cinco posiciones, con 1.174 consultas SQL concurrentes sin errores. Es evidencia de una revisión anterior de la captura. La [medición HTTP inicial](RENDIMIENTO_LECTURA_CIUDADANA_20261016.json) conserva tres ensayos y 90 solicitudes sin errores; el último tuvo percentil 95 de 0,03379 s en 20 solicitudes concurrentes. La [publicación ciudadana](PUBLICACION_CIUDADANA.md) fija la misma versión para datos, métricas, índice y exportaciones y está probada con escrituras concurrentes confirmadas. El [ensayo completo posterior](RENDIMIENTO_CICLO_COMPLETO_20261016.json) verificó 4.261.387 resultados sin puntuación, reanudados sin reinferencia y con origen/punteros intactos. Aún faltan inferencia con modelos aprobados, memoria del intérprete real y ensayo del paquete operativo final.

Una fuente sustituida, un error terminal o falta de espacio bloquea el corte, conserva el anterior y requiere revisión explícita. No se inicia un ciclo automático de recargas. La captura conserva snapshots y sus hashes en el directorio privado de ejecución. La pantalla pública distingue fallo de actualización y fecha del último corte válido.

La [captura optimizada](RENDIMIENTO_CAPTURA_OPTIMIZADA_20261016.json) recorrió las 9.249.545 filas de la copia aislada en 1.304,36 s: 4.261.387 observaciones, los mismos conteos y exclusiones del ensayo anterior y 5.043 consultas ciudadanas sin errores. El ensayo anterior tardó 2.904,76 s; la reducción observada es cercana al 55 %, con cachés y cargas anteriores no controladas. El proceso Python efectivo alcanzó 80.019.456 bytes de RSS y su backend accesible 155.115.520 bytes. No se atribuyen esos valores a toda la máquina ni a la inferencia. Son capturas actuales que deben abstenerse, no evidencia de capacidad predictiva.

Una inferencia terminada publica su archivo y manifiesto mediante el cambio de nombre de un directorio dentro del mismo volumen. Las tentativas interrumpidas quedan separadas. Al reanudar se comprueban insumos, artefactos, código y hash del resultado; no se vuelve a ejecutar el modelo. Cada lote de hasta 1.000 resultados confirma sus filas y posición en la misma transacción. Se reutiliza una plantilla de inserción con parámetros por lote, evitando construir miles de expresiones SQL distintas. La recuperación verifica los recuentos guardados, omite el prefijo confirmado y continúa. Un conflicto o un cursor incoherente no se oculta mediante inserciones ignoradas. Se ha probado la interrupción después de confirmar un lote y la reutilización posterior sin reinferencia ni filas duplicadas.

`scripts/install_risk_autostart.ps1` prepara una tarea Windows del usuario, oculta y al iniciar sesión. Antes de instalar o iniciar, comprueba manifiestos del despliegue, identidad de la base y dos modelos aprobados con programación habilitada. No se instala mientras el índice esté pendiente. El equipo apagado no ejecuta trabajos; se recuperan al volver a iniciar sesión y arrancar los servicios.

## Pendientes para una publicación real

1. Ampliar el inventario hasta reunir decisiones firmes vinculables a SECOP y evidencia de variables en cada etapa.
2. Entrenar ambos modelos reales y superar los criterios independientes. Los ejemplos sintéticos permanecen exclusivamente en pruebas.
3. Comprobar la equivalencia temporal implementada sobre documentos y observaciones reales, y revisar el paquete candidato completo.
4. Validar recursos con modelos aprobados, memoria del intérprete efectivo con modelos aprobados y permisos, recuperación y reversa del despliegue completo. La captura y persistencia masivas de abstenciones ya están comprobadas con lectores HTTP.
5. Solo entonces migrar/activar el candidato local, habilitar la fuente diaria y configurar el inicio Windows. No se ha realizado esa activación.


La [medición del intérprete efectivo](MEMORIA_INTERPRETE_INFERENCIA_20261019.md) confirmó el flujo sintético de ambas etapas con 100.000 filas puntuadas: 19,96 MiB de pico. Esta evidencia complementa la carga masiva previa de abstenciones; no acredita recursos de modelos judiciales reales.
