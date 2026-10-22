# Motor local funcional de señales de riesgo — 20/10/2026

## Corte activo y resultado

El servicio local de lectura usa el artefacto SQLite `Backend/.codex-analytics-postgres/mvp-risk-20261020/full-volume-v3.sqlite` junto con su WAL asociado y responde en `http://127.0.0.1:8011`. La vista ciudadana local está en `http://127.0.0.1:4174/public/indicios`; el panel de analítica administrativa enlaza a la misma evidencia.

- Corte publicado de referencia: **01/10/2026**.
- Cohorte completa: **25/09/2026 a 30/09/2026**, **20.172** operaciones en 71 estratos mensuales.
- Hash SHA-256 de las filas fuente: `ebfdde6415a99a3664e22cbf69cc7a7fef89f2d7cdcfb385a929b8dcf598fb78`.
- **1.787** operaciones tienen una señal estadística confirmada de importe atípico.
- **18.385** no tienen una señal confirmada en las familias evaluables; esto no descarta otros riesgos.
- **1.425** conservan alguna familia no evaluable y **1.372** no tienen ninguna familia evaluable.
- **18.747** tienen una evaluación completa de las familias aplicables en la etapa identificada.
- Etapas observadas en el corte actual: 20.097 convocatoria y 75 adjudicación.

Estos conteos describen la extracción local. No son estimaciones de corrupción ni representan todo SECOP.

## Reglas y pesos

- La señal activa es el presupuesto base fuera de `Q1 − 1,5×IQR` o `Q3 + 1,5×IQR`, con al menos 30 importes positivos de procesos únicos e IQR mayor que cero.
- Los umbrales se calculan una vez por estrato y se reutilizan por operación; la optimización conserva la misma interpolación de cuartiles y límites.
- Los estratos usan mes calendario, tipo de contrato disponible y modalidad. El tipo es un **proxy**: la API de lectura no expone el código oficial de categoría SECOP.
- Los oferentes no están acreditados por los contadores de respuestas. Competencia se abstiene cuando falta oferta válida con ámbito verificable.
- Las ventanas de adjudicación no se calculan sin historial completo e identidad de operación comprobable. Datos faltantes producen `NO_EVALUABLE`, no cero.
- La referencia v8 mantiene un peso igual por familia y publica límites de prioridad solo dentro de cohortes/etapas y aplicabilidades compatibles. No se presenta índice 0–100, probabilidad ni orden total inventado.
- La paginación mantuvo el total e IDs únicos, pero la API no entrega un token transaccional común. La consistencia de generación entre páginas no está certificada.
- La bandera histórica de calidad de datos se muestra aparte y no afecta el motor.

## Interpretación y límites

La salida pública se denomina **señal de riesgo**: es una anomalía que amerita revisar el registro SECOP y sus documentos. No prueba sobreprecio, corrupción, fraude o responsabilidad. El corte es descriptivo con datos observados actualmente y no reconstruye la información disponible cuando se publicó o adjudicó cada operación. No existen modelos entrenados con decisiones firmes vinculadas a este universo, por lo que no se presentan predicciones judiciales.

## Reproducción y operación

La captura y evaluación usan rutas locales de lectura; no escriben PostgreSQL, no migran datos ni sincronizan fuentes:

```powershell
Backend\venv\Scripts\python.exe Backend\scripts\build_mvp_indicios.py
Backend\venv\Scripts\python.exe Backend\scripts\serve_mvp_indicios.py
```

La construcción exige que `http://127.0.0.1:8000/api/procesados/search` responda y se detiene si la cohorte supera 25.000 filas, cambia durante la paginación o contiene identidades locales repetidas. El generador calcula umbrales IQR una sola vez por estrato y no sobrescribe `snapshot-v8.json`; para un nuevo corte debe crearse una nueva versión y cambiarse explícitamente el puntero del servicio. El corte histórico `snapshot-v4.json` se conserva.

Rutas GET del servicio local: `/api/indicios/estado`, `/api/indicios/metodologia`, `/api/indicios/resultados` y `/api/indicios/contrato?raw_id=…`. El proceso enlaza a loopback y permite solo lectura. La paginación devuelve las filas primero y usa `has_more`, evitando calcular el total con un escaneo de los 9,2 millones de filas en cada solicitud. El total exacto sin filtros se toma de los metadatos del corte. La prioridad de revisión se expresa con límites conservadores; los empates y la evidencia faltante no se resuelven por ID.
