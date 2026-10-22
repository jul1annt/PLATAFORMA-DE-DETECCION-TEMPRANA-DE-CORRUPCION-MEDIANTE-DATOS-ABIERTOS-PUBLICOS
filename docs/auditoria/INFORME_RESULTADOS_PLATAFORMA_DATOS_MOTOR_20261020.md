# Informe de resultados de la plataforma, los datos y el motor analítico

**Fecha del informe: 20 de octubre de 2026.**

Informe documental consolidado a partir de las auditorías y validaciones locales existentes. Las cifras conservan la fecha, versión y universo de cada comprobación. Preparar este informe no implicó nuevas cargas, modificaciones de la base publicada, entrenamiento ni contacto con terceros.

## 1. Resumen ejecutivo

La plataforma cuenta con una versión operativa local, un corte SECOP histórico preservado y una base analítica candidata implementada y evaluada para continuar su desarrollo. El plan técnico anterior cerró sus 101 requisitos dentro del alcance acordado. Ese cierre incorporó dos límites aceptados: no se verificó identidad ante DIAN y 18.980 filas antiguas permanecen sin conciliación histórica demostrada.

El corte publicado corresponde al **01/10/2026** y contiene **9.249.545 filas crudas y sus 9.249.545 filas procesadas correspondientes**. No representan 18,5 millones de contratos distintos; tampoco se ha demostrado que cada fila SECOP sea una operación contractual única. Las fuentes permanecen pausadas: no se declara actualización diaria efectiva.

La nueva base del motor separa reglas, construcción de variables, entrenamiento, inferencia y publicación. Corrige comparaciones estadísticas, ventanas y tratamiento de datos ausentes. Deja una política explícita de pesos, herramientas reproducibles y pruebas. **No hay modelos predictivos reales aprobados ni evidencia que permita afirmar precisión en la detección de corrupción.**

## 2. Estado de la plataforma

| Componente | Resultado documentado | Alcance |
| --- | --- | --- |
| Base de datos | PostgreSQL 15.19, base operativa local y copias aisladas de validación | Versión y estado original comprobados el 20/10 |
| API e interfaz | Respuestas HTTP 200 en la última comprobación del 20/10 | API local en puerto 8000 e interfaz en 4173 |
| Consulta ciudadana | Búsqueda, detalle, calidad, tablero y proveedores comprobados en la activación local | Versión histórica; no equivale a desplegar el nuevo motor |
| Administración | Acceso autenticado, autorización y revocación de sesión comprobados | Pruebas de flujo y paquete aislado |
| Procesamiento | Trabajos durables, recuperación, controles de duplicación y cursores | Evita reiniciar indiscriminadamente un trabajo ya existente |
| Cambio de generación SECOP | Suspensión ante sustitución detectada; conserva corte y watermark | No supone que nuevos IDs sean cambios incrementales conciliados |
| Publicación nueva | Infraestructura de resultados persistidos, versiones y activación atómica implementada en el candidato | No activada en la plataforma histórica |
| Actualización diaria nueva | Programación de las 03:00, Bogotá, recuperación y no duplicación implementadas | Desactivada mientras faltan modelos aprobados y aceptación operativa del candidato real |

La plataforma conserva el corte histórico y evita el ciclo automático de borrar y recargar ante reemplazos de la fuente. Esto protege la operación; no demuestra reconciliación incremental entre todas las generaciones futuras.

### Rendimiento comprobado en la versión publicada

El perfil aceptado del 12/10 empleó ocho lectores, cuatro rutas y dos minutos de actividad continua: **9.083 respuestas correctas de 9.083**, sin errores HTTP o de contenido.

| Consulta | Tiempo p95 |
| --- | ---: |
| Búsqueda de 2024 | 0,283 s |
| Búsqueda sin resultados | 0,0065 s |
| Calidad | 0,0048 s |
| Proveedores | 0,308 s |

El p95 es el tiempo por debajo del cual quedó el 95 % de las solicitudes del ensayo. Estos valores corresponden al equipo, versión, carga y condiciones medidas; no garantizan rendimiento para cualquier volumen o demanda. La activación verificó 21 índices válidos de contratos, los triggers de calidad y la equivalencia de sus seis contadores con una agregación independiente del universo completo.

Fuente: [activación local y perfil aceptado](../operacion/ACTIVACION_LOCAL_VERIFICADA_20261012.md). Sus pendientes históricos fueron sucedidos por el [cierre local del 15/10](CIERRE_LOCAL_PLAN_20261015.md).

## 3. Universo y calidad de los datos

### 3.1 Correspondencia y procedencia

En la copia aislada completa se compararon, sin muestreo, las **9.249.545 filas crudas y procesadas**: referencia de origen, identificador reportado normalizado, clave derivada, nombre normalizado y procedencia. Hubo **cero discrepancias de procesamiento o procedencia** en ese alcance. Esto comprueba consistencia del procesamiento, no exactitud de todo lo reportado por la fuente.

La auditoría revisó 36.627 claves derivadas y sus agrupaciones. Los conteos de todos los grupos coincidieron con una agregación independiente; también se verificaron los primeros 100 resultados del repositorio.

### 3.2 Identificador de proveedor

| Clasificación interna del identificador reportado | Filas |
| --- | ---: |
| Ausente o marcador conocido de ausencia | 8.798.585 |
| Formato aceptado sin dígito de verificación reportado | 450.051 |
| Formato aceptado con dígito de verificación coherente | 6 |
| Formato no admitido o ambiguo | 903 |
| Dígito de verificación incoherente | 0 |
| **Total** | **9.249.545** |

La ausencia o marcador afecta al **95,12 %** de las filas. Las 450.057 filas con formato aceptado representan aproximadamente el **4,87 %** y permiten derivar 36.627 claves. Una clave aceptada por formato no acredita titularidad, existencia o situación tributaria ante DIAN. No se debe presentar esa cantidad como proveedores externamente verificados.

Se observaron 181 nombres normalizados asociados a varias claves y 320 claves con varios nombres reportados. Se conservaron las diferencias; los nombres no se usaron para inventar identidades. Estos datos limitan la cobertura de concentración y reiteración por proveedor.

Fuente: [auditoría completa de consistencia SECOP](CONSISTENCIA_PROVEEDORES_SECOP_20261015.md).

### 3.3 Legado y conservación

Las **18.980 filas antiguas** permanecen como legado no conciliado. Coincidencias de contenido o tuplas diagnósticas no se convirtieron en identidades oficiales recuperadas. La limitación histórica fue aceptada expresamente.

El cierre del 15/10 confirmó la conservación de ocho respaldos históricos protegidos y volvió a verificar por SHA-256 el respaldo pequeño específico del original. No se atribuye a este informe una restauración nueva de todos los respaldos grandes. El historial registra cambios observados desde su implantación; no reconstruye intervalos pasados no capturados.

Fuente: [conservación y limitación histórica](CIERRE_LEGADO_SECOP_ACEPTADO_20261015.md).

## 4. Resultados del motor analítico

La versión histórica usa reglas SQL y estadísticas con agregado por proveedor. La nueva base candidata evalúa señales por operación y etapa, con requisitos independientes por indicador.

| Frente evaluado | Universo del ensayo | Resultado obtenido | Interpretación |
| --- | --- | --- | --- |
| IQR corregido | Cohorte completa seleccionada: 1.698 filas | 1.392 comparables; 50 señales, 1.342 sin señal y 306 no evaluables | El 3,59 % de las unidades evaluables mostró importe atípico; no demuestra sobreprecio ni corrupción |
| Ventanas móviles | 13 objetivos con historias admitidas | Conteos 30/90 días contrastados con SQL; todos dieron cero en esos objetivos | Resultado local de esos pares; no describe todo SECOP |
| Composición de familias | 1.698 objetivos y 13 historias admitidas | Cero conteos completos por competencia desconocida | Se conserva evidencia parcial; no se imputa ausencia de datos como ausencia de riesgo |
| Semántica de competencia | 2.536 filas y diccionarios oficiales | Respuestas, invitaciones e interés no acreditan ofertas efectivamente presentadas por lote | Oferentes reales no se habilitan automáticamente |
| Contexto anual | Marco real seleccionado: 1.478 filas | Calidad y exclusión del objetivo coinciden entre referencia y SQL; razón de concentración ausente | Denominador incompleto: no se calcula una proporción sobre el subconjunto conocido |
| Identidades y estratos | Selección de 841 resultados legados | 510 unidades con identidad admisible para el análisis; 331 ambiguas; solo 24 con ambos componentes observados | Análisis descriptivo; no son casos judiciales de entrenamiento |

Estos universos tienen alcances distintos y pueden solaparse. **No se suman como contratos únicos analizados ni permiten estimar prevalencia nacional.** Las señales IQR de reglas nuevas y las del legado tampoco se mezclan.

Las reglas incorporan mínimo de 30 comparables, IQR positivo y agrupación por categoría, modalidad y periodo. Las ventanas cuentan procesos distintos, excluyen el proceso objetivo y conservan fechas y calidad. Los importes usan precisión decimal y no se suman entre monedas no comprobadas. La participación anual no se presenta como cuota monetaria ni HHI.

Fuentes: [cohorte IQR](../analitica/REGLAS_CORREGIDAS_CORTE_2017_20261019.md), [ventanas SQL](../analitica/INTEGRACION_SQL_VENTANAS_20261019.md), [composición](../analitica/COMPOSICION_FAMILIAS_BASE_20261019.md), [competencia](../analitica/SEMANTICA_COMPETENCIA_SECOP_20261020.md), [contexto anual](../analitica/CONTEXTO_ANUAL_BASE_20261020.md) y [estratificación](../analitica/ESTRATIFICACION_BASE_METODOLOGIA_20261019.md).

## 5. Evaluación y decisión de pesos

### 5.1 Legado

Los pesos históricos permanecen en **IQR 1; reiteración 1,5; directa 2**. Se comprobó coherencia aritmética en 2.000 resultados guardados. Después se compararon cinco alternativas de escala y pesos sobre los **31.731 resultados de proveedor de una ejecución completa**. Ese censo pertenece a una ejecución; no a todos los proveedores de SECOP.

El IQR explica el **99,9988 % de la suma ponderada** del censo legado. Esto evidencia dominancia de su escala no acotada frente a componentes de 0 a 10. No significa que el IQR explique ese porcentaje de la corrupción ni de cada puntuación individual.

Igualar los pesos sin cambiar las escalas no resolvió esa dominancia. Las transformaciones acotadas y la referencia empírica congelada cambiaron las prioridades: su coincidencia con el legado en el 5 % superior quedó aproximadamente entre el 70,31 % y el 72,20 %. Ninguna alternativa se seleccionó como mejor detector sin etiquetas válidas.

### 5.2 Referencia para desarrollo

| Familia nueva | Peso | Condición |
| --- | ---: | --- |
| Importe atípico | 1 | IQR evaluable y señal detectada |
| Competencia | 1 | Oferente único solo con modalidad y ofertas comprobadas |
| Concentración/reiteración | 1 | Directas en 90 días o reiteración en 30 días; ambas juntas aportan como máximo uno |

Son pesos **no calibrados**, elegidos como referencia explícita ante la falta de evidencia para privilegiar una familia. Convocatoria admite actualmente la familia IQR; adjudicación puede admitir las tres. Sus conteos no se comparan directamente entre etapas ni se transforman en porcentajes de corrupción.

Los estados `DETECTADA`, `SIN_SENAL`, `NO_EVALUABLE` y `NO_APLICA` permanecen separados. No se publica un total completo cuando una familia aplicable sigue indeterminada. Una condición positiva puede determinar una familia OR aunque otro indicador de esa familia sea desconocido; el detalle se conserva.

Fuentes: [evaluación inicial](../analitica/BASE_MOTOR_Y_PESOS_20261019.md), [normalización y estabilidad](../analitica/NORMALIZACION_Y_ESTABILIDAD_BASE_20261019.md) y [política vigente v7](../analitica/POLITICA_PESOS_BASE_V7.json).

## 6. Modelos y evidencia judicial

Se implementó la infraestructura para **dos modelos independientes: convocatoria y adjudicación**, mediante conjuntos reproducibles de regresiones logísticas con aprendizaje de positivos y casos sin etiqueta. La ausencia de sentencia conocida no se interpreta como negativo confirmado.

La base incorpora separación temporal de entrenamiento/ajuste/evaluación, agrupación de expedientes relacionados, revisión de etiquetas disponibles por fecha, evaluación con proveedores no vistos y comparación con reglas/selección aleatoria. Se prepararon métricas de recuperación y lift al 1 %, 5 % y 10 %, e intervalos por expediente. No se usan nombres, identificadores personales ni documentos judiciales como variables predictoras.

**Estado del inventario: 14 candidatos, cero admisibles. Modelos reales entrenados: cero. Modelos reales aprobados: cero.** Las exclusiones varían: falta de originales o evidencia de firmeza, vínculo SECOP no exacto y/o información temporal insuficiente. Los ensayos sintéticos acreditan funcionamiento del software, no eficacia contra corrupción real.

Por tanto, a la fecha no se pueden reportar precisión real, tasa real de falsos positivos, número de contratos corruptos detectados ni mejora predictiva comprobada frente a las reglas. Tampoco se publica un índice nuevo de 0 a 100. Se respetó la instrucción de no contactar a instituciones o terceros.

## 7. Arquitectura, pruebas y reproducibilidad

Se separaron dominio analítico, variables, entrenamiento, inferencia, persistencia y presentación. Entrenamiento e inferencia usan intérpretes distintos de la API y archivos de dependencias propios. La comprobación efectiva encontró sklearn en entrenamiento y ausencia de SQLAlchemy/FastAPI; inferencia no requiere ninguno de esos tres paquetes. Los trabajos pesados se ejecutan fuera de las solicitudes ciudadanas.

La base conserva hashes, versiones de código y dependencias, evidencia de entrada, referencias congeladas y motivos de abstención. Los controles administrativos rechazan activar modelos sin aprobación. La infraestructura contempla publicación atómica y reversa; no se activó sobre la versión histórica.

### Última validación de la base, 20/10

- **1.057 pruebas backend aprobadas**, cero fallos, errores u omisiones, en aproximadamente 108,64 segundos.
- **11 pruebas de interfaz aprobadas**, cero fallos u omisiones.
- Compilación TypeScript y compilación de producción de la interfaz correctas.
- 31 hashes de archivos de tres validaciones previas cotejados con sus implementaciones actuales; recibo final con 60 archivos de código/dependencias identificados.

Estas pruebas corresponden al candidato local. No se suman las cantidades de baterías históricas como si fueran pruebas distintas, ni se atribuyen todos los cambios posteriores a ensayos anteriores.

### Ensayo aislado de volumen del 16/10

Se recorrieron 9.249.545 filas y se generaron **4.261.387 observaciones**: 3.378.967 de convocatoria y 882.420 de adjudicación. Se excluyeron 4.785.322 por etapa no confirmada y 202.836 por estado fuera del alcance. Es clasificación de cobertura del ensayo, no diagnóstico de corrupción.

Se persistieron 4.261.387 salidas de **abstención** y se comprobó recuperación sin repetir la inferencia. En la fase final de recuperación hubo 6.697 consultas concurrentes, sin errores de lectura, con p95 de aproximadamente 0,0131 segundos. No hubo evaluación predictiva de esas operaciones.

El ensayo no mide inferencia de modelos aprobados ni acredita a volumen completo los materializadores anuales incorporados después. La memoria real del proceso de inferencia no quedó verificada en ese ensayo y no se reporta como medida válida.

Fuentes: [aceptación de la base](../analitica/ACEPTACION_BASE_MOTOR_20261020.md), [recibo final](../analitica/VALIDACION_BASE_FINAL_20261020.json) y [ensayo de volumen y límites](../analitica/RENDIMIENTO_CICLO_COMPLETO_20261016.json).

## 8. Conclusiones y continuación

| Frente | Estado al 20/10 |
| --- | --- |
| Plan técnico anterior | Cerrado: 101/101 dentro del alcance aceptado, con limitaciones históricas y DIAN explícitas |
| Plataforma histórica local | Conservada; consultas y controles operativos verificados; corte 01/10/2026 |
| Datos | Volumen y correspondencia comprobados; fuertes limitaciones de identidad, etapas, competencia e historia temporal |
| Base nueva del motor | Implementada, documentada y probada para continuar su desarrollo |
| Pesos | Históricos conservados; referencia por familias definida; ninguna calibración predictiva acreditada |
| Modelos reales e índice nuevo | Pendientes de datos admisibles, entrenamiento y validación independiente |
| Actualización diaria nueva | Implementada como infraestructura, todavía desactivada |

El siguiente desarrollo debe priorizar evidencia pública utilizable, ofertas efectivas por lote y reconstrucción temporal verificable; ampliar la cobertura sin inferir identidades; y después evaluar los dos modelos con los criterios acordados. Antes de activar se requieren mediciones de recursos del candidato real a volumen completo y aceptación operativa con recuperación y reversa.

**Resultado general:** existe una plataforma local con datos preservados y una base analítica trazable para evolucionar. Se obtuvieron señales estadísticas y se identificaron límites medibles de calidad y puntuación. Todavía no se ha demostrado capacidad predictiva para detectar corrupción ni se han identificado contratos corruptos mediante los nuevos modelos.
