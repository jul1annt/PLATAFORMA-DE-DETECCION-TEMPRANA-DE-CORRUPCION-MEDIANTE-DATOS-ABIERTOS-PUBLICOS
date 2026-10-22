# Validación local del motor — 16/10/2026

## Estado actual

**El plan nuevo sigue pendiente de datos y validación predictiva reales.** Hay código candidato y evidencia local de ingeniería; no se entrenaron ni activaron modelos judiciales reales. El [inventario vigente](INVENTARIO_CASOS_REVISION7_20261018.json) contiene **nueve registros examinados y cero aptos**. La búsqueda no es exhaustiva.

El corte del **01/10/2026**, los respaldos y las **18.980 filas de legado no conciliado** se conservan. La base publicada mantiene OID **24577**, esquema `3c19a8f7e2d0` y paquete `794d185`. Las comprobaciones consolidadas son de lectura sobre ese despliegue. No se activó el nuevo índice ni se instaló la tarea Windows. El plan anterior conserva su cierre y alcance.

## Implementado

- Dominio, reglas, variables, evidencia, entrenamiento, inferencia, persistencia y presentación separados. API y procesador conservan sus dependencias; entrenamiento e inferencia tienen entornos propios.
- Dos modelos PU por etapa, manifiestos predictivos, hashes, referencias congeladas y evaluación temporal por expediente. Los identificadores sirven para trazabilidad y separación, no como predictores.
- IQR por categoría/modalidad/año con mínimo de 30 operaciones independientes; reiteraciones y ventanas móviles. Datos faltantes se evalúan por indicador.
- Registro de evidencia física por operación/etapa. La misma observación revisada se usa al entrenar e inferir; una captura actual no reconstruye el pasado. Revisiones contradictorias se abstienen.
- Vínculos judiciales con revisión de hechos y parte resolutiva por operación. Nulidades, absoluciones, investigaciones o fraude contractual no se propagan como positivos de corrupción.
- Rutas administrativas autenticadas; resultados públicos paginados, evidencia y metodología; contexto de proveedor separado. La interfaz distingue calidad, anomalía y señal de riesgo.
- Cadena diaria a las 03:00 de Bogotá, cola durable, protección de generación, cursores y reanudación. Un cambio de fuente pausa la actualización; no genera ciclos de borrado y recarga.
- Publicación atómica de datos e índice, historiales incrementales y agregados persistidos. La reversa restaura ambos punteros y pausa la programación. Un corte de solo abstenciones no se publica.
- Captura sin agregados actuales innecesarios ni conteo previo completo. Persistencia por plantilla de inserción, con filas y cursor confirmados juntos.
- Lanzador con hilos limitados y cierre del árbol propio por tiempo máximo. En Windows, el Job Object cierra sus descendientes también ante muerte del propietario. Su registro de ejecución es independiente del manifiesto predictivo; cambios de orquestación no acoplan el modelo a la API.

## Evidencia comprobada

La [consolidación estructurada](VALIDACION_LOCAL_20261016.json) registra identidades, hashes y alcances. La [auditoría de requisitos](AUDITORIA_PLAN_MOTOR_20261016.md) mantiene los pendientes explícitos.

| Comprobación | Resultado y alcance |
| --- | --- |
| Suite backend vigente | **581 pruebas correctas**, cero fallos/errores; PostgreSQL aislado y procesos ML separados |
| Frontend | 11 pruebas, TypeScript, Vite y ESLint correctos; no hubo cambios de interfaz en esta última revisión |
| Contrato API | OpenAPI, tipos y matriz de acceso comprobados en la revisión de interfaz |
| Migración/reversa | Hasta `f67b120ce841` en OID 82244, rol ordinario; reversa vacía y rechazo transaccional con evidencia presente; marcador sintético retirado |
| Variables por etapa | Equivalencia de entrenamiento/inferencia con documentos sintéticos; evidencia real todavía pendiente |
| Publicación durante escrituras | 48 lecturas conservaron el corte durante ocho actualizaciones confirmadas; exportaciones y reversa coherentes |
| Captura optimizada completa | **9.249.545 filas en 1.304,36 s** (21 min 44 s), frente a 2.904,76 s; mismos conteos y exclusiones |
| Lectores durante captura | 5.043 solicitudes, cero errores, p95 0,01470 s; dos lectores concurrentes |
| Inferencia de ingeniería completa | 4.261.387 observaciones en 531,02 s; todas abstenciones, sin modelos entrenados o aprobados |
| Persistencia y recuperación completas | **4.261.387 filas verificadas**, sin índices puntuados; origen y punteros sin cambios; cero reinferencias en las reanudaciones |
| Última reanudación y validación | 1.723,02 s para continuar desde 1.837.000 filas hasta completar y validar el total; no es el tiempo de insertar toda la población desde cero |
| Lectores durante última reanudación | 6.697 solicitudes, cero errores, p95 0,01312 s; dos lectores concurrentes |
| Memoria de captura | Pico RSS del Python efectivo: 80.019.456 bytes; backend accesible: 155.115.520 bytes; no representa memoria total |
| Memoria del último escritor | Pico RSS de 100.839.424 bytes; no representa toda la base o el equipo |
| Relación de resultados del ensayo | 12.726.919.168 bytes físicos, incluidos índices y almacenamiento asociado; no se extrapola a producción |
| Contención de procesos Windows | Árboles sintéticos detenidos por plazo en 5,13 s y por salida abrupta del supervisor en 1,83 s; hashes del código comprobado |
| Recuperación del worker tras salida abrupta | Trabajo sintético recuperado con el mismo UUID, dos intentos y sin duplicados; descendientes detenidos y marcador retirado en OID 82244 |
| Dependencias | Locks y hashes comprobados; API sin NumPy/scikit-learn añadidos. Auditoría conservada: cero vulnerabilidades conocidas reportadas en esa consulta |

## Interpretación del ensayo masivo

La [captura optimizada](RENDIMIENTO_CAPTURA_OPTIMIZADA_20261016.json) conservó 4.261.387 observaciones: 3.378.967 de convocatoria y 882.420 de adjudicación. Excluyó 4.785.322 filas sin etapa confirmada y 202.836 por estado fuera del alcance. No excluyó filas por falta de normalización. La reducción observada del tiempo de captura fue cercana al **55 %**; las cachés y cargas anteriores no están controladas y los archivos difieren al retirar contextos actuales innecesarios.

El [recorrido completo](RENDIMIENTO_CICLO_COMPLETO_20261016.json) terminó correctamente en la copia OID 75045. El primer proceso confirmó 1.000 filas. Una reanudación avanzó hasta 1.837.000 antes de una interrupción intencional para separar cargas de disco; la siguiente terminó las 4.261.387 y comprobó el total. Se reutilizó el archivo original verificado en 12,56 s y 15,23 s, sin volver a ejecutar inferencia. Las tres fases acumularon 25.094 lecturas HTTP sin errores; la captura optimizada fue otro ensayo separado.

Es una prueba de captura, abstención, archivos, escritura y recuperación. **No acredita capacidad predictiva ni rendimiento de un modelo aprobado.** La memoria del intérprete real de inferencia no se midió: la muestra inicial correspondía al lanzador Windows y no se usa como memoria del estimador.

La [comparación de inserciones](RENDIMIENTO_ESCRITURA_LOTES_20261016.json) utilizó cuatro transacciones revertidas de 10.000 resultados: plantilla 3,72–4,26 s; expresión anterior 4,39–10,84 s. No se extrapola a rendimiento sostenido. Se conservan también las mediciones anteriores de [captura parcial](RENDIMIENTO_CAPTURA_20261016.json) y [lectura ciudadana](RENDIMIENTO_LECTURA_CIUDADANA_20261016.json).

El [control de procesos](CONTROL_PROCESOS.md) verifica el plazo y la salida abrupta del supervisor de árboles sintéticos Windows. La recuperación integrada utilizó el worker y PostgreSQL reales en la base vacía, con una función de entrenamiento ficticia: no creó modelos ni tocó fuentes. No sustituye el ensayo HTTP del paquete final. El registro `.process.execution.json` conserva los hashes del lanzador y ejecutable, límites y estado sin introducirlos como dependencias de aprobación predictiva.

## Casos y límites históricos

La [revisión judicial 5](HALLAZGOS_JUDICIALES_REV5_20261016.md) conserva una sentencia sobre hechos de 2020–2022 y un [seguimiento de identidad](SEGUIMIENTO_VINCULO_SEP077_20261016.json). Hay correspondencia de un proceso en la copia, pero difieren los IDs de fila actuales y guardados; no hay identidad de adjudicación o firmeza verificadas. No se sustituyeron IDs ni se crearon positivos. El inicio 2020 del adaptador describe cobertura, no una prohibición de otros casos verificables.

Se documentaron dos incidencias durante la revisión: un entrenamiento sintético agotó su plazo antes de igualar el límite de hilos, y una simulación POSIX necesitó corrección para ejecutarse en Windows. Se conservan sus registros y las ejecuciones posteriores correctas. Algunas comprobaciones nuevas de conexión al despliegue publicado agotaron el tiempo; las repeticiones correctas se distinguen de esos fallos, sin presumir su causa.

## Pendientes para completar el plan

1. Decisiones firmes, vínculos exactos, cronología de investigación y observaciones históricas utilizables suficientes para ambas etapas.
2. Entrenamiento real y evaluación cronológica por expediente y proveedores no vistos; mínimo técnico de cinco expedientes positivos por bloque y mejora independiente en recuperación al 5 % con intervalo del 95 % por encima de cero.
3. Equivalencia temporal comprobada sobre documentos y observaciones reales, con cobertura y sesgos documentados.
4. Ensayo del paquete operativo final: permisos de objetos instalados, recursos con modelos aprobados, lectores y fallo/reanudación del servidor HTTP completo. La contención Windows y recuperación del worker ya se verificaron con supervisores y tareas sintéticas; no sustituyen ese ensayo.
5. Activación local, actualización diaria e inicio Windows solo después de superar lo anterior. Mientras falte evidencia, se conserva la plataforma actual y la nueva publicación queda pendiente.

La [revisión judicial 6](HALLAZGOS_JUDICIALES_REV6_20261016.md) incorpora una absolución confirmada relativa al contrato 086 de Necoclí. Se mantiene separada de la pista del contrato 095. No es una etiqueta positiva ni negativa; la firmeza y cualquier correspondencia SECOP siguen sin acreditarse.

## Ensayo HTTP nativo del candidato

La [comprobación aislada](VALIDACION_HTTP_AISLADA_20261016.json) inició el código candidato mediante Uvicorn en 127.0.0.1:8017, con la base OID 82244. Verificó tres consultas públicas, validación de etapa y las diez operaciones administrativas con tres clases de credenciales ausentes o inválidas: 30 rechazos correctos. Una cuenta temporal propia permitió comprobar login, cuatro consultas autenticadas, cinco rechazos ante entradas o aprobación ausentes y revocación al cerrar sesión. Se retiraron exclusivamente esa cuenta y sus sesiones y se detuvo el servidor. No se restauró la secuencia de IDs del entorno aislado.

El rol ordinario satisfizo los permisos analíticos examinados. Los recuentos de fuentes, trabajos, evidencias, modelos y resultados y los punteros no cambiaron. No hubo modelos entrenados, publicación ni tarea Windows. Este ensayo amplía la evidencia de autenticación HTTP; no sustituye los flujos con modelos reales aprobados, la interfaz integrada o el paquete operativo final.

## Actualización 18/10/2026: corpus público desde fuentes oficiales

Ante la ausencia de expedientes aportados, se inició la [construcción del corpus judicial](CONSTRUCCION_CORPUS_JUDICIAL.md). Se conservaron siete fuentes de descubrimiento y cuatro providencias enlazadas, con procedencia, hashes y reanudación sin descargas repetidas. Herramientas documentales separadas de API y modelos; 16 pruebas específicas correctas. No se añadieron positivos aptos: el entrenamiento y la publicación continúan pendientes.

La [revisión judicial 7](HALLAZGOS_JUDICIALES_REV7_20261018.md) investigó 1.101.679 líneas de archivos oficiales históricos sin escribir sus 3,18 GB descomprimidos. Halló una correspondencia candidata del contrato 497/2013 y separó otra operación 362/2013 que no coincide con la sentencia. Se preservan los IDs publicados; faltan firmeza y evidencia temporal válida. Herramientas del corpus: 27 pruebas correctas; ningún positivo admitido.

## Actualización 18/10/2026: revisión de firmeza

La [revisión 8](HALLAZGOS_JUDICIALES_REV8_20261018.md) distingue los avisos que abren recursos de una firmeza confirmada. La admisión exige revisión expresa del efecto y localizador documental. El [inventario vigente](INVENTARIO_CASOS_REVISION8_20261018.json) conserva diez candidatos y cero aptos. La [validación consolidada del 18/10](VALIDACION_LOCAL_20261018.json) confirma 591 pruebas backend correctas, migración y reversa aisladas y conservación del despliegue publicado mediante lectura. Los informes anteriores son evidencia de sus respectivas revisiones. No se entrenaron ni aprobaron modelos reales.

## Seguimiento documental: revisión 9, 18/10/2026

La [revisión 9](HALLAZGOS_JUDICIALES_REV9_20261018.md) y su [inventario](INVENTARIO_CASOS_REVISION9_20261018.json) conservan once candidatos, cero aptos. Se localizaron recursos efectivamente interpuestos, otra correspondencia histórica del contrato 362/2012 y SP1919-2025 sobre Ruta del Sol. Los IDs de proceso, fila y adjudicación siguen separados. Solo cambió el registro documental; no se repitieron pruebas del código inalterado ni cargas ya comprobadas. Persisten los requisitos de evidencia y evaluación previos a la publicación.

## Validación del 19/10/2026: contabilidad de particiones

Se corrigió el rechazo de particiones que excluyen filas por motivos cronológicos: el total verificado se concilia ahora con filas usadas y excluidas. La auditoría de partición queda enlazada al artefacto por hash y se comprueba al aprobar. Las **606 pruebas del backend** terminaron sin fallos, errores ni omisiones; incluyen entrenamiento sintético con exclusiones y rechazo de informes incoherentes. La [evidencia consolidada](VALIDACION_PARTICIONES_TEMPORALES_20261019.json) registra hashes, resultado de pruebas y lecturas de las bases aislada y publicada. No se repitieron migraciones ni cargas. La [explicación del cambio](PARTICIONES_TEMPORALES_20261019.md) conserva los límites: faltan casos reales suficientes y no se activó publicación.

## Validación del 19/10/2026: registro de modelos

La persistencia aplica la política completa de aprobación también a resultados recuperados. Se conservan candidatos no aprobados con estado falso y se rechazan aprobaciones incoherentes. La suite completa pasó **613 pruebas**. La [explicación y límites](REGISTRO_MODELOS_20261019.md) y la [evidencia consolidada](VALIDACION_REGISTRO_MODELOS_20261019.json) conservan los resultados, incluidos los fallos iniciales de preparación sintética y su corrección. No hay modelos judiciales reales aprobados ni publicación nueva.

Se [recuperaron las sentencias de primera y segunda instancia](SENTENCIAS_SAMAI_20261019.md) del índice 166 de SAMAI. Esta adquisición resuelve una carencia documental de Ruta del Sol; faltan revisión completa, firmeza fechada, vínculo SECOP exacto y datos históricos por etapa. No se admitieron positivos adicionales.


## Validación monetaria del 19/10/2026

Se añadió la política de evidencia v2 para impedir mezclar VPIT, pesos constantes, moneda extranjera y escalas con importes nominales COP. Exige unidades, significado, importe original, transformación y revisión documental explícita. La [explicación](BASE_MONETARIA_20261019.md) y la [validación consolidada](VALIDACION_BASE_MONETARIA_20261019.json) registran **656 pruebas backend correctas**. La base aislada quedó sin modelos o evidencias sintéticas y el esquema original se conservó. Faltan corpus judicial suficiente y evaluación real; no se activó publicación.


## Memoria efectiva de inferencia: 19/10/2026

Se midió desde el intérprete real el CLI con dos modelos sintéticos de 25 miembros y 2.000/100.000 observaciones evaluables. Pico máximo 19,96 MiB; incremento entre tamaños de 52 KiB. Se verificaron manifiestos, código, cantidades y prefijo reproducible. Ver [método y límites](MEMORIA_INTERPRETE_INFERENCIA_20261019.md). Es evidencia del flujo sintético puntuado; quedan pendientes recursos con modelos judiciales aprobados y despliegue completo. No se accedió a las bases ni se publicaron resultados.


## Revisión documental 11, 19/10/2026

El [inventario 11](INVENTARIO_CASOS_REVISION11_20261019.json) conserva catorce registros candidatos y cero aptos. Se incorporaron Guainía y Putumayo y se separó un caso de estafa del objetivo de corrupción. Se corrigió una asociación a un PDF de otro procesado antes de admitir evidencia. La [revisión](HALLAZGOS_JUDICIALES_REV11_20261019.md) y la [validación documental](VALIDACION_CORPUS_REV11_20261019.json) conservan alcance parcial, exclusiones, hashes y cobertura corregida de años. Continúan pendientes firmeza fechada, vínculos exactos y evidencia temporal suficiente; no se entrenaron modelos ni se modificó la publicación.

## Revisión documental 12, 19/10/2026

Se ampliaron los perfiles de búsqueda histórica a Guainía y Putumayo, conservando Arauca como valor predeterminado. Las [tres lecturas completas](CORRESPONDENCIAS_HISTORICAS_GUAINIA_PUTUMAYO_20261019.json) verificaron 2.131.839 líneas y conservaron siete correspondencias candidatas, separando ocho coincidencias numéricas distintas. Se recuperaron contrato y resolución de Putumayo y resolución 0175 de Guainía. La [revisión 12](HALLAZGOS_JUDICIALES_REV12_20261019.md) documenta discrepancias de fechas, importes y disponibilidad, 37 pruebas correctas y alcance parcial. El [inventario vigente](INVENTARIO_CASOS_REVISION12_20261019.json) conserva catorce registros y cero aptos; no hay nuevas etiquetas ni modelos.

## Revisión 13: declaración posterior de firmeza, 19/10/2026

La [consulta oficial de AEP012-2024](FIRMEZA_GUAINIA_RELATORIA_20261019.json) confirma ejecutoria de SEP079-2023 en las consideraciones, pero su descarga devuelve un aviso de indisponibilidad. La política judicial v2 admite providencias posteriores con declaración expresa y fechada, manteniendo originales, hashes, revisión y vínculo específico. Las [674 pruebas backend](VALIDACION_FIRMEZA_DECLARADA_20261019.json) pasaron; las lecturas de OID 24577 y 82244 conservaron sus esquemas y no hay publicación analítica nueva. El [inventario 13](INVENTARIO_CASOS_REVISION13_20261019.json) mantiene cero aptos: el extracto parcial no se registró como prueba completa de firmeza. Ver [alcance y pendientes](HALLAZGOS_JUDICIALES_REV13_20261019.md).

## Revisión 14: expediente Centros Poblados, 19/10/2026

Se identificaron CUI 11001600000020240094600 y NI 455754 mediante ANDJE y CPNU. El registro menciona sentencia condenatoria en firme y conserva fechas distintas de actuación/registro; no tiene documentos adjuntos. La [revisión 14](HALLAZGOS_JUDICIALES_REV14_20261019.md) distingue esa anotación de una sentencia o constancia original. El [inventario](INVENTARIO_CASOS_REVISION14_20261019.json) sigue con catorce candidatos y cero aptos. La [validación documental](VALIDACION_CENTROS_POBLADOS_20261019.json) confirma hashes, exclusiones y cobertura; no hubo cambios de implementación, acceso a bases ni activación.
