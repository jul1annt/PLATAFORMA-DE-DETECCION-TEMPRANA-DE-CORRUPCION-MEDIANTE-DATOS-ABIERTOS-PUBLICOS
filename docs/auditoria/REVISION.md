# Revisión técnica del backend y frontend

Fecha: 21 de septiembre de 2026 (America/Bogota).

**Resultado: el proyecto presenta bloqueos de seguridad, exactitud de datos y compilación. La lógica de negocio todavía no está concentrada en el backend.** Esta entrega es una auditoría; no se han corregido los archivos de aplicación ni actualizado sus dependencias.

## Alcance y evidencia

Se revisaron rutas y dependencias de autenticación, ingesta, transformación, analítica, modelos, migración inicial, contratos de API, servicios y pantallas React, manifiestos y dependencias. Se comprobó el esquema OpenAPI y se reprodujo un defecto de contabilidad con objetos simulados.

No se ejecutaron escrituras contra PostgreSQL, sincronizaciones externas, explotación de endpoints ni migraciones sobre una base real. No se inspeccionaron valores secretos de `.env`. La auditoría no certifica un despliegue que pudiera añadir controles externos; los hallazgos corresponden al código del repositorio.

| Comprobación | Resultado |
| --- | --- |
| Estado inicial de Git | Sin cambios pendientes |
| `npm run build` | Falla: 8 diagnósticos TypeScript |
| `npm run lint` | Falla: 54 errores y 1 advertencia |
| `npm audit --json` | 13 paquetes afectados: 9 altos, 2 moderados y 2 bajos |
| `venv/Scripts/python.exe -m pip check` | Sin incompatibilidades declaradas en el entorno instalado |
| `python -m pytest -q` en el venv | No ejecutable: `pytest` no está instalado |
| Cuatro funciones de `tests/test_normalization.py`, ejecutadas directamente con `runpy` | 4 pasan; no equivale a una suite de integración |
| Análisis sintáctico Python | 72 archivos del backend válidos, excluyendo venv |
| Importación de `main` y generación de OpenAPI | Correctas, sin iniciar el scheduler |
| Operaciones de gestión/procesamiento en OpenAPI | 11 sin requisito de autenticación |
| Reproducción del conteo de campos faltantes | 5 campos ausentes producen 10 incrementos |
| `pip-audit` sobre `requirements.txt` | 8 paquetes afectados; 36 entradas reportadas, con duplicados; 20 identificadores distintos |

Los resultados completos se conservan en `npm-audit.json` y `python-audit.json` en esta carpeta. `pip-audit` se instaló en un entorno temporal independiente y se ejecutó con `--no-deps --disable-pip`: audita las versiones explícitas del manifiesto, no certifica que un entorno limpio pueda resolverlas ni cubre dependencias no declaradas.

## Hallazgos prioritarios

### 1. Crítico — Operaciones administrativas accesibles sin autenticación

**Evidencia:** `Backend/modules/ingesta/controller/IngestaController.py:10`, `Backend/modules/transformacion/controller/transformacionController.py:44`, `Backend/modules/analitica/controller/AnaliticaController.py:36` y `:333`. `Backend/gateway/router.py` incluye estos routers sin una dependencia de seguridad global. El esquema OpenAPI confirma la ausencia de seguridad en las once operaciones de escritura/procesamiento.

Un cliente que alcance la API puede crear, cambiar o eliminar fuentes, probar conexiones, iniciar sincronizaciones, reprocesar contratos, ejecutar los tres análisis, cambiar pesos y recalcular riesgo sin enviar JWT. La pantalla de login y `ProtectedRoute` no impiden llamadas HTTP directas. Además, `/app` conserva pantallas de gestión sin `ProtectedRoute` (`Frontend/src/router/index.tsx:69`).

**Corrección:** exigir administrador activo en cada operación administrativa del servidor; mantener públicas solo las consultas aprobadas. Proteger o retirar las rutas antiguas. Los servicios administrativos React deben enviar la credencial: actualmente `Frontend/src/api/axios.ts` no tiene interceptor de autenticación y `analiticaService.ts` usa `fetch` sin `Authorization`. Probar acceso anónimo, token inválido, expirado, usuario inactivo y administrador válido.

### 2. Crítico — Registro público de administradores

**Evidencia:** `Backend/modules/auth/controller/AuthController.py:26` y `Backend/modules/auth/service/AuthService.py:77`.

`POST /api/auth/register` crea administradores sin autenticación ni condición de primer usuario. El comentario que indica deshabilitarlo en producción no implementa ninguna protección; `exists_any_admin()` tampoco se usa para restringirlo. Cerrar las otras rutas no basta mientras cualquier visitante pueda convertirse en administrador.

**Corrección:** aprovisionar el primer administrador mediante comando controlado y restringir altas posteriores a administradores autorizados. Evitar un registro inicial público basado únicamente en contar usuarios, que también requiere controlar concurrencia.

### 3. Alto — Solicitudes del servidor a destinos arbitrarios y posible envío de credenciales

**Evidencia:** `Backend/modules/ingesta/dto/request.py:9`, `Backend/modules/ingesta/services/IngestaService.py:48`, `Backend/modules/ingesta/adapters/secop_adapter.py:43` y `:83`.

El endpoint configurable acepta cualquier URL HTTP/HTTPS y se entrega a `requests.get`, sin lista de destinos permitidos ni restricción de redirecciones. `HttpUrl` valida formato, no impide destinos locales o privados. Combinado con el hallazgo 1, un usuario anónimo puede inducir solicitudes desde el servidor hacia la red interna. También puede cambiar el endpoint de una fuente conservando su `api_key`; el adaptador enviará esa clave en `X-App-Token` al nuevo destino.

**Corrección:** permitir solo orígenes y rutas de proveedores aprobados, HTTPS, controlar redirecciones y aplicar restricciones de salida de red. Validar tanto altas como actualizaciones y la solicitud final. No reutilizar credenciales automáticamente al cambiar de origen.

### 4. Alto — Administrador desactivado conserva acceso con un token vigente

**Evidencia:** `Backend/modules/auth/service/AuthService.py:92` y `Backend/modules/auth/repository/AuthRepository.py:14`.

El login filtra `is_active`, pero la resolución de cada token busca únicamente por ID. Desactivar una cuenta no bloquea su token existente. Asimismo, `/logout` solo devuelve un mensaje; no invalida el token en el servidor.

**Corrección:** comprobar actividad en cada petición protegida. Si cerrar sesión debe revocar acceso inmediatamente, implementar sesiones o revocación del token; documentar y probar esa semántica. Como endurecimiento adicional, limitar intentos de login y validar longitud/calidad de credenciales en el backend.

### 5. Alto — Dashboard calcula métricas globales sobre 50 contratos

**Evidencia:** `Frontend/src/services/procesadosService.ts:95`, `:100`, `:121`, `:136` y `:150`; `Backend/modules/transformacion/controller/transformacionController.py:121`.

`fetchAllItems()` envía `size=1000` a `/search`, que acepta `limit` y por defecto devuelve 50. Rankings de proveedores, distribución de anomalías y riesgo se calculan en el navegador con esa página. El porcentaje de alto riesgo divide el conteo parcial por el total global. Incluso cambiar `size` por `limit` seguiría dando resultados incompletos cuando haya más de 1000 contratos.

**Corrección:** agregar en PostgreSQL sobre todo el universo filtrado y devolver métricas y series desde endpoints del backend. Definir la identidad de proveedores mediante NIT cuando esté disponible y una política explícita para los restantes. El navegador debe limitarse a representar los resultados.

### 6. Alto — Ausencia de clasificación interpretada como riesgo bajo

**Evidencia:** `Frontend/src/services/procesadosService.ts:138`, `Frontend/src/pages/PublicProcesados.tsx:156`, `Backend/modules/transformacion/dto/response.py:9` y `Backend/modules/transformacion/model/ContratoProcesado.py:7`.

El frontend espera `clasificacion_riesgo` y `datos_modificados`, pero ni el modelo ni la respuesta de contratos procesados incluyen esos campos. `getRiskDistribution()` convierte la clasificación ausente en `BAJO`; así puede mostrar como bajo riesgo contratos que nunca fueron clasificados. El parámetro `solo_alto_riesgo` tampoco existe en el controlador de búsqueda y se ignora.

**Corrección:** acordar si el indicador representa riesgo de contrato o de proveedor, publicar ese resultado en el contrato API e implementar su filtro en servidor. Representar explícitamente `SIN_EVALUAR`. Retirar temporalmente los indicadores de cambios si aún no existe una fuente de verdad para ellos.

### 7. Alto — Conteos de campos faltantes duplicados y reprocesamiento no idempotente

**Evidencia:** `Backend/modules/transformacion/services/trasformacionservice.py:248`, `:312` y `:166`.

La detección incrementa el contador y `_actualizar_estadisticas()` vuelve a incrementarlo al guardar anomalías nuevas. La reproducción con repositorio simulado produce diez incrementos para cinco campos faltantes. Además, al forzar reprocesamiento, la detección incrementa antes de decidir que un registro no cambió; repetir el proceso puede seguir inflando porcentajes.

**Corrección:** hacer que la detección sea una función sin efectos en la persistencia; calcular estadísticas a partir de anomalías vigentes, o actualizarlas una sola vez mediante diferencias y dentro de una transacción coherente. Probar primera ejecución, repetición sin cambios, corrección de un dato y fallo parcial.

### 8. Alto — Reprocesar no actualiza las anomalías de contratos existentes

**Evidencia:** `Backend/modules/transformacion/services/trasformacionservice.py:135` y `:160`.

La rama de actualización modifica el contrato existente, pero solo la rama de inserción vincula y agrega las anomalías detectadas. Un contrato puede dejar de ser sospechoso cuando una fecha antes futura ya no lo sea, mientras su detalle conserva la anomalía anterior.

**Corrección:** reemplazar o reconciliar anomalías vigentes por contrato en la misma transacción, con un historial separado si se necesita trazabilidad. Recalcular estadísticas desde ese estado vigente.

### 9. Alto — Sincronización incompleta se marca como exitosa y adelanta el cursor

**Evidencia:** `Backend/modules/ingesta/adapters/secop_adapter.py:13` y `:67`; `Backend/modules/ingesta/services/IngestaService.py:105`; `Backend/core/scheduler.py:50`.

El adaptador está limitado a 10000 registros. Al alcanzar el límite termina normalmente y el servicio guarda la hora actual como última sincronización. La próxima ejecución comienza desde esa fecha de publicación y puede omitir permanentemente el resto del histórico. La paginación tampoco fija un orden estable. Adicionalmente, el repositorio usa `on_conflict_do_nothing` por proceso, por lo que no actualiza contratos ya importados que cambien en origen.

**Corrección:** distinguir resultados completos y parciales, persistir un cursor estable de la fuente y avanzarlo solo después de confirmar cada tramo. Diseñar la captura de actualizaciones mediante fecha de modificación y upsert/versionado según las garantías de la fuente.

### 10. Alto — La compilación del frontend está rota

**Evidencia:** ejecución de `npm run build`.

Tres errores de tipos en los `formatter` de Recharts: `AnomalyChart.tsx:81`, `RiskChart.tsx:73` y `TopProvidersChart.tsx:63`. Las funciones exigen valores que el tipo de Recharts permite que sean opcionales o de otro tipo. Otros cinco diagnósticos corresponden a símbolos no utilizados en `AdminDashboard.tsx`, `PublicProcesados.tsx` y `exportUtils.ts`.

**Corrección:** adaptar los tipos y el tratamiento de valores de los tooltips y eliminar símbolos sin uso. Mantener `build` y `lint` como controles obligatorios antes de integrar cambios; no desactivar las reglas para ocultar los problemas.

### 11. Medio — Búsqueda local posterior a la paginación

**Evidencia:** `Frontend/src/pages/PublicProcesados.tsx:183` y `Frontend/src/services/procesadosService.ts:69`.

La búsqueda de texto y las sugerencias consultan solo los contratos cargados. Un resultado existente en otra página puede aparecer como inexistente; el total y la paginación permanecen asociados a un conjunto distinto del mostrado.

**Corrección:** implementar búsqueda y autocompletado en backend; filtrar antes de contar y paginar. Conservar en React el texto ingresado, el debounce, la navegación y el renderizado.

### 12. Medio — Exportación CSV permite fórmulas procedentes de datos externos

**Evidencia:** `Frontend/src/utils/exportUtils.ts:15`.

Escapar comillas protege la estructura CSV, pero no neutraliza cadenas como `=1+1`, que una hoja de cálculo puede interpretar como fórmula al abrir el archivo. Nombres y otros textos proceden de fuentes externas. No se ejecutó ninguna fórmula ni se abrió un archivo malicioso.

**Corrección:** definir una política de exportación que preserve los campos textuales como texto y neutralice prefijos de fórmulas, incluidos espacios/caracteres de control relevantes. Centralizar la selección y preparación de los datos exportados en el backend, con pruebas de contenido y filtros.

### 13. Medio — Configuración HTTP inconsistente

**Evidencia:** `Frontend/src/api/axios.ts:4` frente a `Frontend/src/services/procesadosService.ts:3` y `analiticaService.ts`.

Parte de la aplicación usa `VITE_API_URL` y otra parte siempre llama a `http://localhost:8000`. Configurar una API desplegada no corrige todas las peticiones; en HTTPS algunas pueden además bloquearse por contenido mixto. Los distintos clientes también dispersan el manejo de errores y credenciales.

**Corrección:** centralizar URL, credenciales, expiración y errores en un cliente HTTP compartido; configurar CORS en el servidor para los orígenes reales.

### 14. Medio — Programador bloquea el bucle asíncrono y duplica el flujo de ingesta

**Evidencia:** `Backend/core/scheduler.py:10`, `:41` y `Backend/main.py:8`.

El job es `async` pero ejecuta `requests` y SQLAlchemy síncronos sin ceder el control. Durante una ingesta lenta puede bloquear el bucle de eventos del worker. Cada proceso de la API inicia su propio scheduler; `max_instances=1` no coordina procesos diferentes. El flujo programado tampoco usa el servicio que registra historial para la sincronización manual.

**Corrección:** ejecutar los trabajos en un worker dedicado o mecanismo que no bloquee la API, usar exclusión compartida por fuente y reutilizar el mismo caso de uso con historial y recuperación de errores.

### 15. Medio — Riesgo combinado mezcla proveedores por nombre

**Evidencia:** `Backend/modules/analitica/repository/repository.py:673`.

La consulta final une y agrupa por nombre del proveedor y selecciona `MAX(nit_proveedor)`. Si hay dos NIT distintos con el mismo nombre normalizado, combina sus señales y atribuye el resultado a uno de los NIT. La existencia de estos casos en la base no se verificó.

**Corrección:** usar una identidad estable de proveedor, preferentemente NIT validado, y resolver explícitamente los casos sin identificador. Mantener trazabilidad de las ejecuciones y el universo de datos de cada componente del riesgo.

## Dependencias y alcance real de los avisos

### Frontend

El resultado npm contiene 13 paquetes afectados. Incluye `axios`, `react-router`, `react-router-dom`, `xlsx`, `vite`, `postcss` y dependencias transitivas. El conteo representa paquetes afectados, no 13 explotaciones confirmadas ni necesariamente 13 CVE distintos.

`xlsx` no tiene corrección automática disponible según el resultado de npm. Su uso observado es exportación; no se encontró aquí un flujo de importación de planillas que demuestre explotación de los avisos de lectura. Revisar la distribución mantenida o sustituir esta dependencia como parte del traslado de exportaciones al servidor. La documentación del fabricante explica su política y versiones: https://docs.sheetjs.com/docs/miscellany/security/.

El aviso de Vite sobre rutas Windows afecta al servidor de desarrollo bajo condiciones específicas, incluida exposición a la red. No demuestra exposición del sitio estático construido; el `vite.config.ts` revisado no activa `host`. El fabricante identifica 8.0.16 como corrección de ese aviso concreto: https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff.

### Backend

| Paquete fijado | Entradas del auditor | Versiones de corrección citadas por el auditor |
| --- | ---: | --- |
| anyio 4.13.0 | 2 | 4.14.2 |
| cryptography 48.0.0 | 7 | 48.0.1, 49.0.0, 50.0.0, según aviso |
| ecdsa 0.19.2 | 2 | Sin corrección indicada |
| idna 3.14 | 2 | 3.15 |
| pyasn1 0.6.3 | 6 | 0.6.4 |
| pydantic-settings 2.14.1 | 1 | 2.14.2 |
| python-multipart 0.0.28 | 6 | 0.0.30 y 0.0.31, según aviso |
| starlette 1.0.0 | 10 | 1.0.1, 1.1.0, 1.3.0 y 1.3.1, según aviso |

Hay entradas repetidas en la respuesta del servicio: 36 entradas corresponden a 20 IDs distintos. No asumir que estas actualizaciones pueden hacerse aisladamente: resolver compatibilidad con FastAPI, Pydantic y las demás restricciones en un entorno limpio.

La presencia de un paquete no demuestra que se alcance el código vulnerable. Por ejemplo, el JWT usa HS256 por defecto y el aviso `ecdsa` se refiere a operaciones de firma ECDSA; el código revisado no monta `StaticFiles` ni configura `NestedSecretsSettingsSource`, relevantes para varios avisos de Starlette y pydantic-settings. No se certifica ausencia de exposición en configuraciones externas no revisadas.

El manifiesto Python fija versiones sin hashes y mezcla dependencias directas/transitivas; faltan herramientas de pruebas declaradas. Separar dependencias de aplicación y desarrollo, producir un bloqueo reproducible con hashes y establecer auditoría en CI. `pip check` solo comprueba compatibilidad declarada del entorno instalado, no seguridad.

## Distribución de responsabilidades requerida

| Debe controlar el backend | Puede permanecer en el frontend |
| --- | --- |
| Autorización, estado de administradores y validación definitiva | Estado visual de sesión y navegación |
| Reglas, umbrales y clasificación de riesgo/calidad | Colores y componentes según una clasificación recibida |
| Totales, porcentajes, rankings y series globales | Dibujo y geometría de gráficos; formato de cifras |
| Búsqueda, filtros de negocio, conteo y paginación de datos | Parámetros de consulta, debounce y controles de paginación |
| Sincronización, normalización, auditoría y reprocesamiento | Mostrar progreso y resultado de trabajos |
| Selección de datos y preparación segura de reportes/exportaciones | Solicitar y descargar el archivo |

También trasladar las agregaciones de `ComparativaSincronizaciones.tsx:15`, los conteos de estados de `AdminSyncLogs.tsx:104` y la clasificación de calidad con umbrales de `PublicDashboard.tsx:247`. Las validaciones de formulario para respuesta inmediata pueden permanecer, pero siempre deben repetirse de forma autoritativa en servidor.

Una interfaz React necesita lógica de presentación. El criterio verificable es que cambiar o evitar el JavaScript del navegador no cambie permisos, reglas, resultados oficiales ni validaciones obligatorias.

## Orden de corrección y criterios de aceptación

1. Cerrar registro y operaciones administrativas; restringir destinos de ingesta; conectar credenciales del frontend y rechazar cuentas inactivas. Verificar 401/403 sin efectos secundarios en todas las operaciones protegidas.
2. Corregir conteos, reconciliación de anomalías y cursor de sincronización. Probar idempotencia y reanudación tras fallos con PostgreSQL desechable y fuentes simuladas.
3. Definir contratos de API para métricas, riesgo, filtros, autocompletado y exportaciones. Probar con más de 1000 contratos y proveedores homónimos con NIT distintos. El total, el filtro y los resultados deben corresponder al mismo universo.
4. Resolver compilación y ESLint, incluyendo hooks condicionales en `Input.tsx:11` y `Select.tsx:12`. El hook debe ejecutarse siempre y luego elegirse el ID.
5. Actualizar dependencias con resolución y pruebas de compatibilidad; conservar excepciones de auditoría solo cuando tengan una justificación concreta de alcance y revisión.
6. Incorporar pruebas de autorización, API/frontend, ingesta, métricas, reprocesamiento y migraciones en CI, junto con build, lint y auditoría de dependencias.

La revisión detectó además almacenamiento directo de `api_key` en `FuenteDatos` pese a que la documentación anuncia cifrado Fernet, errores internos devueltos con `str(e)` y múltiples proveedores de sesión SQLAlchemy. Corregir estos puntos durante la consolidación del backend. No se observó cifrado de aplicación de esa clave en el flujo de creación/actualización revisado; esto no evalúa un posible cifrado del volumen o de la infraestructura.
