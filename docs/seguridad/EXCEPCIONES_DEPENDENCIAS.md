# Registro de excepciones de dependencias

Revisión: 2026-09-26.

## `ecdsa` — PYSEC-2026-1325 — resuelto por reemplazo

- **Hallazgo:** `ecdsa 0.19.2` entraba transitivamente por `python-jose`. El [aviso del mantenedor](https://github.com/tlsfuzzer/python-ecdsa/security/advisories/GHSA-wj6h-64fc-37mp) describe un ataque de temporización Minerva para operaciones ECDSA/ECDH y declara que no planea publicar una corrección.
- **Alcance:** la aplicación usa JWT `HS256`; no necesita operaciones ECDSA para autenticar.
- **Tratamiento:** se reemplazó `python-jose` con `PyJWT 2.15.0`, fijado en `requirements.in`; se regeneraron ambos locks con hashes y se eliminaron del entorno del proyecto los paquetes `ecdsa`, `python-jose`, `pyasn1` y `rsa`.
- **Verificación:** `pip-audit -r requirements.lock`, `pip-audit -r requirements-dev.lock` y la auditoría del entorno instalado no detectan vulnerabilidades. `pip check` pasa. CI ejecuta `pip-audit` sin ignorar este identificador.

La captura inicial se conserva en `docs/auditoria/python-audit.json` como evidencia de la línea base; no representa el estado actual de dependencias.

## `source-map-js` — GHSA-68fv-2mgg-jv7q — actualización

El 2026-10-06, la instalación limpia para integración detectó `source-map-js 1.2.1` en el lock frontend. Se actualiza exclusivamente esa dependencia transitiva a `1.2.2`, versión corregida indicada en el [aviso revisado](https://github.com/advisories/GHSA-68fv-2mgg-jv7q) y publicada por el [mantenedor](https://github.com/7rulnik/source-map-js/releases/tag/v1.2.2). La auditoría del lock actualizado devolvió cero vulnerabilidades; la instalación, pruebas y build del nuevo artefacto se deben verificar antes de usarlo en integración. No se añade una excepción al auditor de CI.
