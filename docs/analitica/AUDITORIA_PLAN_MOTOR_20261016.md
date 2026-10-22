# Auditoría del alcance del motor

Estado del plan predictivo ampliado: **modelos reales y activación pendientes**. El entregable inmediato precisado por el usuario —base para desarrollar después— tiene su [aceptación separada del 20/10](ACEPTACION_BASE_MOTOR_20261020.md). Esta distinción no declara cerrado el despliegue predictivo ni reabre el cierre del plan anterior. La tabla siguiente conserva evidencias de sus fechas; la aceptación enlazada reúne el estado actual de la base.

El [inventario vigente](INVENTARIO_CASOS_REVISION16_20261019.json) tiene catorce registros candidatos, tres con conducta clasificada como corrupción, uno como fraude contractual y cero aptos para entrenamiento. Se localizaron siete correspondencias históricas candidatas en Guainía/Putumayo, confirmación de ejecutoria de Guainía en la relatoría e identificación institucional del proceso de Duque en Centros Poblados con anotación de sentencia en firme en CPNU. La revisión específica de seis contratos de Guainía conserva una discrepancia de 100 COP sin conciliar fuentes. SECOP II confirma el enlace entre fases y dos lotes; el ID de fila actual difiere del guardado y no se concilia. Los originales y fechas todavía no admitidos se conservan como investigación. No hay modelos reales aprobados. La tabla resume la evidencia más reciente indicada, mientras las secciones de actualización conservan la cronología de revisiones anteriores.

## Requisitos y evidencia disponible

| Requisito del plan | Evidencia actual | Estado |
| --- | --- | --- |
| Inventario judicial con motivos de exclusión | Inventario 16 con catorce registros candidatos y cero aptos; siete correspondencias candidatas; alcance de seis contratos de Guainía revisado sin admitir operaciones ni resolver la discrepancia monetaria de 069 | Inventario actualizado; admisión y suficiencia no demostradas |
| Firmeza, vinculación SECOP exacta y clasificación de conductas | `corpus.py`, `domain.py`, registro administrativo y hashes; política v2 admite providencias posteriores que declaren la firmeza, con fecha expresa y localizador | Implementado y probado; faltan casos reales que cumplan |
| Corrupción separada de fraude y otras irregularidades | Objetivo positivo `CORRUPCION`; fraude identificado separadamente y excluido como positivo | Implementado y probado |
| Sin etiquetas extendidas a todo el proveedor | Vínculo exacto por operación y etapas revisadas explícitamente | Implementado y cubierto por pruebas |
| Unidad fila/proceso/lote/adjudicación | Claves por fuente/proceso/adjudicación; abstención ante alias ambiguos; el adaptador no confirma lotes | IQR legado corregido y probado: presupuesto por proceso, importe por adjudicación; sin fabricar n=30 con alias |
| Evidencia temporal anterior a investigación | Fecha documentada de primera investigación, campos con disponibilidad y hash; sin sustituirla por la fecha de sentencia | Reforzado; faltan observaciones históricas utilizables |
| Procedencia comprobable de cada variable histórica | Registro administrativo, documentos físicos y revisión explícita; índice por fila/etapa; captura actual y revisiones contradictorias se abstienen | Misma observación histórica en entrenamiento e inferencia, probada en ambas etapas con fixtures; evidencia real pendiente |
| Expedientes relacionados fuera de bloques distintos | Unión transitiva por documento judicial, autoridad/radicado y relaciones declaradas | Implementado y probado |
| Dos modelos PU independientes | Entrenamiento por etapa, ensambles reproducibles, referencias congeladas | Probado con datos sintéticos; cero modelos judiciales reales |
| Validación cronológica y etiquetas disponibles en cada fecha | Bloques independientes, etiquetas futuras tratadas como no etiquetadas también durante ajuste; auditoría de exclusiones enlazada al modelo | Implementado; regresión de contabilidad comprobada el 19/10; evaluación real pendiente |
| Recuperación/lift y comparación con reglas y azar | Métricas al 1/5/10 %, presupuesto exacto fraccional, bootstrap por expediente, proveedores no vistos; adjudicaciones distintas conservadas | Implementado y probado con datos sintéticos; evaluación real pendiente |
| Variables y reglas independientes de la API | Dominio puro, construcción de variables, materialización SQL, entrenamiento, inferencia y presentación separados | Implementado |
| Dependencias bloqueadas y procesos separados | Lock de entrenamiento, inferencia estándar, manifiestos y hashes; el inicio comprueba el intérprete efectivo de inferencia y rechaza compartir entorno con la API | Implementado y comprobado con intérpretes reales en aislamiento; paquete operativo final pendiente |
| Entrenamiento independiente de actualización diaria | Rutas administrativas y trabajos distintos; el scheduler solo solicita inferencia | Implementado |
| Índice 0–100 con referencia fija por etapa/versión | Percentil y manejo de empates; sin probabilidad de corrupción | Implementado |
| Resultados por operación, trazabilidad y abstenciones | Metadatos también sin índice, valores monetarios sin pérdida decimal, referencias, fecha de evaluación y contexto | Fixture visual comprobada en escritorio y móvil; revisión del despliegue completo pendiente |
| Lectura pública paginada y versiones anteriores | Consultas con `cut_id`; solo cortes publicados; recuentos persistidos y lectura de una misma versión | Implementado y probado |
| Controles administrativos protegidos | Casos, evidencias de variables, entrenamiento, modelos, activación y reversa con autenticación | HTTP nativo aislado y paquete completo aislado: login y consultas correctos, activación sin modelos rechazada y logout revoca acceso. Ensayo con modelos reales y despliegue final pendientes |
| Actualización 03:00 Bogotá y recuperación | Cola durable, claves estables, reanudación por hijos, archivo de inferencia reutilizable y cursor confirmado junto con cada lote | Ensayo de ingeniería completo: 4.261.387 resultados, todas abstenciones; recuperados sin reinferencia ni duplicados. Activación operativa pendiente |
| Fuente sustituida sin bucles de borrado/recarga | Protección existente de generación, pausa del corte y programación ante errores | Integrado; sin cambios destructivos en este trabajo |
| Activación atómica | Revisiones e historiales incrementales de cuatro tablas, agregados persistidos, punteros ciudadano/analítico en una transacción | Implementado y probado; lecturas y exportaciones fijan el mismo corte. 48 lecturas durante ocho cambios confirmados sin mezclar versiones |
| Control eficiente de cambios | Migración `bd71c6a4046f`, revisiones y recuentos transaccionales; lecturas de dos filas | Pruebas de inserción, actualización, borrado, rollback y upserts correctas |
| Recursos y lectores concurrentes sobre volumen real | Copia OID 75045: 9.249.545 filas capturadas en 1.304,36 s; 4.261.387 resultados persistidos y verificados. Última reanudación: 6.697 solicitudes HTTP, cero errores, p95 0,01312 s | Ingeniería de captura/abstención/recuperación completa. Memoria real sintética puntuada: 19,96 MiB para 100.000 filas. Faltan recursos y memoria con modelos aprobados y ensayo operativo |
| Control de procesos y separación del modelo | Inicio suspendido y Job Object privado Windows; plazo, salida abrupta del propietario y recuperación real de trabajo en OID 82244 comprobados con tareas sintéticas. Registro separado del manifiesto predictivo | Paquete aislado: dos ciclos API/interfaz/worker, recuperación de trabajo sin duplicados y cierre de todos los procesos. Modelos reales pendientes |
| Migración, reversa y activación local | OID 82244: head `f67b120ce841`; reversa vacía y rechazo con evidencia comprobados el 18/10; 744 pruebas backend el 19/10, interfaz recompilada y dos ciclos del paquete aislado | Corregidos conflicto Windows de escritura y selección del runtime de autoinicio. Registro de tarea simulado y rechazo real comprobados; disparador, publicación y reversa finales pendientes |
| Conservación del corte y legado | OID 24577 conserva esquema `3c19a8f7e2d0`, paquete `794d185`, fuentes/trabajos pausados; HTTP 200 | Comprobado mediante lectura; sin identidades inferidas al legado |

## Pendientes que impiden declarar el plan completo

El [seguimiento de acceso judicial](SEGUIMIENTO_ACCESO_JUDICIAL_20261019.md) registra que el usuario autorizó las consultas y descargas públicas, pero la herramienta continúa denegando CPNU, el repositorio de la Corte y SECOP II. Se solicitó retirar el bloqueo guardado o administrado. La nueva pista de Cartagena permanece fuera del registro canónico hasta adquirir originales. Las herramientas de corpus pasaron 39 pruebas después de corregir la validación previa de catálogos; no se generaron etiquetas nuevas.

1. Obtener decisiones firmes, vínculos exactos y datos anteriores a investigación suficientes para ambas etapas. El límite 2020 del adaptador describe cobertura, sin prohibir otros casos verificables. Falta poblar el registro con observaciones reales válidas.
2. Acreditar con esos documentos reales la equivalencia temporal ya implementada y probada con fixtures; una captura actual nunca se puntúa como un estado histórico.
3. Entrenar y evaluar ambos modelos reales con comparación independiente, cobertura, sesgos e intervalos por expediente.
4. Validar inferencia y recursos con modelos realmente aprobados, incluida memoria del intérprete efectivo. La captura, inferencia de abstenciones, persistencia completa, espacio y recuperación con lectores HTTP ya se comprobaron en la copia de volumen real.
5. Completar la aceptación operativa con modelos reales aprobados: permisos y dos ciclos de inicio/parada, autenticación y recuperación de un trabajo sin modelos se comprobaron en el paquete aislado. Faltan autoinicio, publicación/reversa, recuperación con modelos aprobados y revisión visual del paquete final.
6. Activar publicación y programación local únicamente después de superar lo anterior; mientras falte evidencia suficiente, conservar la plataforma actual conforme a la condición aprobada.

### Comprobación de inicio, 19/10/2026

Se corrigió una omisión de permisos en el comprobador de inicio: ahora incluye cola de trabajos, fuentes, historiales de ingesta y secuencias de inserción del ciclo. [Detalle y límites](PERMISOS_CICLO_DIARIO_20261019.md). La batería completa pasó 691 pruebas; esta validación no sustituye el ensayo operativo final ni aprueba modelos judiciales. No se concedieron permisos ni se cambió la publicación.

Se añadió después la [comprobación del intérprete de inferencia](INICIO_INFERENCIA_AISLADA_20261019.md): procesos reales verifican aislamiento, código predictivo y separación del entorno de la API sin importar dependencias de entrenamiento. La nueva batería completa pasó 707 pruebas. El inicio del paquete operativo final sigue pendiente.

El [ensayo del paquete aislado](PAQUETE_AISLADO_20261019.md) completó dos ciclos API/interfaz/worker y comprobó autenticación, rechazo de activación sin modelos, recuperación sin duplicados y parada. Un primer intento detectó un conflicto Windows al reemplazar el estado durante lecturas; se corrigió y la batería completa pasó 731 pruebas. No se activaron modelos, publicación ni tarea Windows.

La [revisión del autoinicio](AUTOINICIO_PAQUETE_20261019.md) corrigió la ruta de Python y la selección de scripts desde los manifiestos. Pasaron 13 pruebas PowerShell con comandos del Programador de tareas simulados y dos rechazos reales del instalador empaquetado por falta de modelos aprobados. La batería completa pasó 744 pruebas. La tarea no se instaló ni se ejecutó el disparador de inicio de sesión; esa aceptación final permanece pendiente.

## Interpretación de las pruebas

Las pruebas sintéticas verifican software, integridad y recuperación. No acreditan capacidad de detección real ni firmeza judicial. Los primeros ensayos de volumen identificaron lecturas demasiado costosas y motivaron cambios; no se consideran aprobación de rendimiento diario. No se extrapola el tiempo de unos pocos lotes a toda la inferencia.

El [ensayo completo](RENDIMIENTO_CICLO_COMPLETO_20261016.json) leyó las 9.249.545 filas e hizo inferencia de ingeniería sobre 4.261.387 observaciones; todas se abstuvieron. Confirmó primero 1.000 resultados, reutilizó el archivo sin reinferencia y avanzó hasta un cursor durable de 1.837.000 antes de una interrupción intencional para separar las cargas de disco. Después completó y verificó las **4.261.387 filas**, sin cambiar origen ni punteros. La captura optimizada terminó en 1.304,36 s, con los mismos conteos y 5.043 lecturas HTTP sin errores. La memoria del intérprete real de inferencia no fue comprobada y no se sustituye por la del lanzador Windows. No se entrenaron ni aprobaron modelos reales.

La suite del backend completó **591 pruebas sin fallos** en la validación consolidada del 18/10/2026, incluyendo control de procesos y separación de sus manifiestos. Una ejecución anterior agotó el tiempo del entrenamiento sintético: 554 pruebas pasaron y una falló; una prueba de simulación POSIX requirió corrección para ejecutarse en Windows. Las repeticiones correctas y sus registros se conservan. La reversa aislada y la lectura del despliegue original se volvieron a comprobar después de la ejecución correcta.

La plataforma publicada conserva el corte del **01/10/2026**. El nuevo índice y la tarea Windows siguen desactivados.




## Actualización 18/10/2026: revisión de firmeza

La [revisión 8](HALLAZGOS_JUDICIALES_REV8_20261018.md) distingue los avisos que abren recursos de una firmeza confirmada. La admisión exige revisión expresa del efecto y localizador documental. El [inventario vigente](INVENTARIO_CASOS_REVISION8_20261018.json) conserva diez candidatos y cero aptos. La [validación consolidada del 18/10](VALIDACION_LOCAL_20261018.json) confirma 591 pruebas backend correctas, migración y reversa aisladas y conservación del despliegue publicado mediante lectura. Los informes anteriores son evidencia de sus respectivas revisiones. No se entrenaron ni aprobaron modelos reales.

## Seguimiento documental: revisión 9, 18/10/2026

La [revisión 9](HALLAZGOS_JUDICIALES_REV9_20261018.md) y su [inventario](INVENTARIO_CASOS_REVISION9_20261018.json) conservan once candidatos, cero aptos. Se localizaron recursos efectivamente interpuestos, otra correspondencia histórica del contrato 362/2012 y SP1919-2025 sobre Ruta del Sol. Los IDs de proceso, fila y adjudicación siguen separados. Solo cambió el registro documental; no se repitieron pruebas del código inalterado ni cargas ya comprobadas. Persisten los requisitos de evidencia y evaluación previos a la publicación.

## Validación del 19/10/2026: contabilidad de particiones

Se corrigió el rechazo de particiones que excluyen filas por motivos cronológicos: el total verificado se concilia ahora con filas usadas y excluidas. La auditoría de partición queda enlazada al artefacto por hash y se comprueba al aprobar. Las **606 pruebas del backend** terminaron sin fallos, errores ni omisiones; incluyen entrenamiento sintético con exclusiones y rechazo de informes incoherentes. La [evidencia consolidada](VALIDACION_PARTICIONES_TEMPORALES_20261019.json) registra hashes, resultado de pruebas y lecturas de las bases aislada y publicada. No se repitieron migraciones ni cargas. La [explicación del cambio](PARTICIONES_TEMPORALES_20261019.md) conserva los límites: faltan casos reales suficientes y no se activó publicación.

## Validación del 19/10/2026: registro de modelos

La persistencia aplica la política completa de aprobación también a resultados recuperados. Se conservan candidatos no aprobados con estado falso y se rechazan aprobaciones incoherentes. La suite completa pasó **613 pruebas**. La [explicación y límites](REGISTRO_MODELOS_20261019.md) y la [evidencia consolidada](VALIDACION_REGISTRO_MODELOS_20261019.json) conservan los resultados, incluidos los fallos iniciales de preparación sintética y su corrección. No hay modelos judiciales reales aprobados ni publicación nueva.

Se [recuperaron las sentencias de primera y segunda instancia](SENTENCIAS_SAMAI_20261019.md) del índice 166 de SAMAI. Esta adquisición resuelve una carencia documental de Ruta del Sol; faltan revisión completa, firmeza fechada, vínculo SECOP exacto y datos históricos por etapa. No se admitieron positivos adicionales.


## Revisión documental 10, 19/10/2026

El [inventario actualizado](INVENTARIO_CASOS_REVISION10_20261019.json) conserva once candidatos y cero aptos. Se incorporaron la sentencia original de instancia y su apelación al candidato Ruta del Sol, clasificando la conducta acreditada y separando la referencia judicial de la identidad SECOP todavía no resuelta. Ver [hallazgos y exclusiones](HALLAZGOS_JUDICIALES_REV10_20261019.md). El CAPTCHA de esta consulta fue autorizado y resuelto; ese estado sustituye la espera descrita en revisiones anteriores. No se entrenaron modelos ni se cambió la publicación.

## Registro oficial SECOP consultado el 19/10/2026

Se abrió el detalle oficial de 09-1-41316 mediante navegador, separando los contratos 001 y 002. Se conservaron resolución 641, prepliego y pliego de adenda 12 con fechas del índice. La [revisión de correspondencia](CORRESPONDENCIA_SECOP_RUTA_SOL_20261019.md) distingue VPIT, presupuesto global, versiones y fechas contradictorias. Los IDs hallados en un conjunto community siguen como pistas. La [consulta de avisos de Casación Penal](AVISOS_CASACION_20261019.md) no acreditó firmeza específica. No se admitieron etiquetas ni observaciones históricas.


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
