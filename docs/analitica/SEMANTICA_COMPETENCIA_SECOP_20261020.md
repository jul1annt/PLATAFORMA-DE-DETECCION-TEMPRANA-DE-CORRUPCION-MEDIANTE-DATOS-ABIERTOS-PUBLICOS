# Competencia: semántica auditada y contadores separados de oferentes

## Decisión de uso

La revisión de los campos disponibles terminó con una limitación concreta: **los contadores de respuestas guardados no acreditan por sí solos ofertas presentadas, ofertas válidas ni competencia de cada lote**. No se habilitó la variable `oferentes` a partir de ellos. La [política v6](POLITICA_PESOS_BASE_V6.json) registra esta decisión y conserva los pesos.

`Backend/modules/motor_riesgo/competition_context.py` clasifica esos campos como contexto descriptivo. Su salida mantiene `actual_bidders=null`, `model_values={}` y `scoring_eligible=false`, incluso cuando el contador vale uno, la modalidad es competitiva y se declara un lote. No sustituye un campo ausente por invitaciones, interés u otro contador.

## Fuentes comprobadas

Se descargaron únicamente archivos públicos de `datos.gov.co`, sin mensajes ni solicitudes a funcionarios o instituciones:

1. [Diccionario SECOP II con vigencia indicada de junio de 2021](https://www.datos.gov.co/api/views/s2tk-xck7/files/b208b4ff-27c8-4a17-8caf-8ebf0865f0d7?download=true&filename=DiccionarioDeDatosAbiertos.pdf). La primera página identifica el conjunto `p6dx-8zbt`; la tabla relevante está en la segunda.
2. [Archivo publicado como diccionario 2022 de procesos](https://www.datos.gov.co/api/views/8scu-28fr/files/ffa9c16f-d9df-4e8d-b826-4eb5520953c7?download=true&filename=Diccionario+de+Datos+Abiertos+2022+Procesos+de+Contratacion+.pdf), cuyos encabezados internos indican mayo de 2021. Se revisó la tabla de la página física 6, numerada internamente 3 de 7. No se infirió una versión semántica de 2022 por su nombre de archivo.
3. [Metadata actual del conjunto](https://www.datos.gov.co/api/views/p6dx-8zbt.json), conservada con hash y verificación del identificador del dataset y sus columnas.

Las dos tablas PDF se renderizaron e inspeccionaron. El análisis de texto y los hashes se conservaron localmente. El informe referencia por hash las definiciones originales, que permanecen en los archivos fuente; no copia todo el diccionario. La metadata consultada describe el esquema actual y no demuestra cómo se conocía cada variable en 2017.

## Qué permiten interpretar los campos

| Campo API | Uso admitido en esta base |
|---|---|
| `proveedores_invitados` | Invitaciones reportadas; no confirma participación |
| `proveedores_con_invitacion` | Invitación directa registrada |
| `proveedores_que_manifestaron` | Interés registrado |
| `respuestas_al_procedimiento` | Respuestas del procedimiento; la metadata actual incluye a proveedores y entidad |
| `respuestas_externas` | Actividad de respuesta externa |
| `conteo_de_respuestas_a_ofertas` | Contador de respuestas vinculado a ofertas; no distingue proveedores |
| `proveedores_unicos_con` | Proveedores con respuestas registradas; no certifica presentación o validez de ofertas |
| `numero_de_lotes` | Lotes declarados del proceso; no asigna respuestas a una adjudicación |

La descripción de respuestas al procedimiento cambia de énfasis entre los diccionarios antiguos y la metadata actual. No se impuso una igualdad o desigualdad entre contadores que pueden medir universos distintos. La falta de definición común impide tratar uno como sustituto de otro.

Los enteros no negativos se clasifican como cero, uno o múltiples. Ausencia e invalidez se conservan separadas. Se rechazan booleanos, fracciones, no finitos y cantidades superiores al límite técnico de entero de 32 bits. Ese límite protege el procesamiento; no es un umbral de riesgo. Cero lotes no se convierte en un lote único, ni cero respuestas en cero oferentes acreditados.

## Cobertura de los datos guardados

Se leyeron **2.536 filas distintas** de la base original OID 24577, en una transacción repetible de solo lectura. Son la unión de las 1.698 filas de la cohorte directa de 2017 y las 841 del subconjunto UUID anterior; hay tres filas compartidas. No hubo nueva selección por puntaje ni escritura de datos operativos. No es un censo ni una muestra representativa de toda la contratación.

| Observación | Resultado |
|---|---:|
| Filas revisadas | 2.536 |
| Procesos distintos observados | 2.456 |
| Filas que pasan el chequeo de identidad de operación utilizado | 1.900 |
| Modalidades competitivas reconocidas por el diccionario | 584 |
| De esas 584, identidad de operación admisible | 401 |
| Contador de proveedores con respuestas igual a cero | 235 |
| Contador igual a uno | 1.770 |
| Contador mayor que uno | 531 |
| Lotes declarados como cero | 2.291 |
| Lotes declarados como uno | 2 |
| Lotes declarados múltiples | 243 |

El contador de proveedores con respuestas está presente y es un entero válido en todas las filas seleccionadas. Esa disponibilidad no resuelve su significado ni su relación con ofertas efectivamente presentadas.

En las 584 filas de modalidades competitivas reconocidas, el contador de proveedores con respuestas vale uno en 169, cero en 15 y más de uno en 400. Solo una declara exactamente un lote; 406 declaran cero y 177 varios. **No se convirtieron esas 169 observaciones en 169 señales de oferente único.**

La auditoría distingue filas y procesos para no multiplicar una observación compartida por varias adjudicaciones. También registra discrepancias o faltantes entre filas seleccionadas del mismo proceso. Esa comprobación no demuestra consistencia de todas sus filas en la fuente: el marco completo de cada proceso no fue extraído. El chequeo global de identidad de esta extracción usa las claves almacenadas exactas; no concilia variantes nuevas de identidad.

## Ejecución y validación

```powershell
Backend/venv/Scripts/python.exe Backend/scripts/risk_competition_audit.py --input Backend/.codex-analytics-postgres/competition-fields-input-20261020.json --source-manifest Backend/.codex-analytics-postgres/competition-public-sources-20261019/manifest.json --output auditoria-competencia-nueva.json
```

El comando desconectado comprueba hashes de los diccionarios y metadata, rechaza cambios y no sobrescribe una salida. Usa biblioteca estándar; no incorpora dependencias a API, entrenamiento o inferencia. Los archivos originales y siete archivos de implementación se conservaron. La copia congelada ejecutada con `-I -S` reprodujo la salida byte por byte.

Pasaron **97 pruebas enfocadas**, incluidas **28 nuevas** del contexto y su CLI. Comprueban tipos inválidos, ceros, lotes, múltiples adjudicaciones, discrepancias, fuentes desconocidas y ausencia de sustituciones. Dos casos adicionales dentro de esas 28 verifican que la captura real de variables, tanto en convocatoria como adjudicación, no mapea contadores poblados a `oferentes`. Las otras pruebas cubren la composición y la cobertura existentes. No es una nueva ejecución completa del backend.

La extracción y comprobación inicial tardó aproximadamente 107 segundos. Los análisis posteriores utilizaron los archivos guardados, sin repetir consultas. Es una adquisición pequeña con accesos a datos dispersos; ese tiempo no representa ni garantiza el rendimiento del universo completo.

El [informe final](AUDITORIA_CAMPOS_COMPETENCIA_REV2_20261020.json) contiene las observaciones y agregados separados por selección. El [recibo de validación](VALIDACION_CAMPOS_COMPETENCIA_20261020.json) enlaza fuente, consultas, hashes, imágenes revisadas, código, pruebas y reproducción. Se retiraron tres salidas intermedias de ensayo; los datos de entrada, fuentes públicas, corte histórico y respaldos se conservaron.

## Consecuencia para el motor y siguiente paso

La revisión semántica de estos ocho campos queda documentada; **el oferente real sigue sin estar acreditado**. Para habilitarlo hará falta evidencia nueva que distinga ofertas presentadas o válidas y su ámbito por lote, junto con la disponibilidad temporal requerida. No se reinterpretarán estos mismos contadores para completar artificialmente la familia.

La evaluación conjunta anterior mantiene competencia sin evaluar y ningún puntaje completo. Los pesos históricos y el punto de referencia por familia no cambian. El siguiente trabajo de la base es revisar el denominador y la cobertura anual de concentración; no repetir esta interpretación ya resuelta de los contadores existentes.
