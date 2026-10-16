# Propuesta de alcance para P06 — únicamente SECOP

Estado: **propuesta pendiente de decisión del usuario**. No acredita cierre de P06 ni modifica el checklist de 97/101 completados.

## Dato confirmado

El usuario confirmó el 15/10/2026 que solo dispone de contratos SECOP y no hay registros DIAN. La aplicación puede procesar SECOP con esta disponibilidad. No hay una fuente independiente disponible para contrastar quién es el titular real de cada NIT.

## Criterio original conservado

«Verificar el backfill y los valores históricos de identidad de proveedor sobre una copia aislada y contrastar los datos existentes con el registro DIAN.»

El contraste externo sigue sin realizarse. La confirmación de ausencia de registros describe los insumos disponibles; no constituye por sí sola una prueba de ese contraste ni el cierre del requisito original.

## Sustitución propuesta para P06

«Verificar, sobre la copia aislada existente del corte SECOP aceptado del 01/10/2026, la consistencia del identificador reportado por SECOP y de la clave normalizada de proveedor en todo el universo histórico procesado. Conservar la procedencia y el valor reportado; cuantificar identificadores ausentes, formatos no aceptados y DV incoherentes; comprobar que las claves almacenadas coinciden con las reglas implementadas y que los agregados no fusionan proveedores solo por nombre. Documentar expresamente que no se realizó contraste de identidad con DIAN.»

### Evidencia necesaria después de aceptar el cambio

- Identidad exacta de la copia aislada, revisión y versión del código de normalización; fuentes y trabajos pausados durante la comprobación.
- Cotejo de todo el universo del corte, con cantidades evaluadas y discrepancias. Si el recorrido queda incompleto o se usa una muestra, no declarar verificación completa.
- Correspondencia de los identificadores reportados por SECOP con su representación procesada y su clave derivada. Explicar los casos sin clave y resolver discrepancias del procesamiento.
- Comprobación de agrupaciones y conservación de la procedencia. Los nombres coincidentes por sí solos no prueban que dos proveedores sean la misma entidad.
- Informe de solo lectura que declare el alcance, método, límites, duración y ausencia de escrituras. Reutilizar la copia retenida y las evidencias anteriores; no volver a cargar ni reprocesar por defecto los 9.249.545 contratos.

La comprobación de formato o DV es una validación interna. El informe debe presentar la identidad como reportada por SECOP y dejar el contraste externo como **no realizado por ausencia de fuente de referencia**. Tampoco acredita existencia, titularidad o situación tributaria histórica del proveedor.

## Efecto sobre los otros pendientes

P01 conserva su aplicación administrativa de firewall y pruebas efectivas de tráfico. P05 y P12 conservan sus requisitos de reconciliación histórica de filas SECOP: una decisión sobre DIAN no resuelve los IDs oficiales ausentes en los registros antiguos.

## Decisión requerida

Aceptar esta sustitución limita P06 a consistencia y procedencia de datos SECOP. Después habrá que ejecutar y verificar las comprobaciones descritas antes de cerrarlo. Conservar el criterio original mantiene P06 pendiente del contraste externo.
