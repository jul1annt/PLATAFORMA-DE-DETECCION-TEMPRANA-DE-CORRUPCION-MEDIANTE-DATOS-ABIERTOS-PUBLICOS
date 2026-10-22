from modules.ingesta.dto.response import (
    ComparativaFuenteDTO,
    SincronizacionHistorialResponseDTO,
    SincronizacionHistorialPaginaDTO,
    SincronizacionHistorialResumenDTO,
)
from modules.ingesta.model.SincronizacionHistorial import EstadoSync
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from shared.errors import IngestaError
import logging
import uuid

from core.config import settings
from ..repository.IngestaRepository import IngestaRepository
from ..adapters.adapter_factory import get_adapter
from ..dto.request import FuenteDatosCreateDTO, FuenteDatosUpdateDTO
from ..dto.response import FuenteDatosResponseDTO, ConexionTestResponseDTO
from ..model.FuenteDatos import FuenteDatos
from ..security import encrypt_api_key, endpoint_origin, validate_source_endpoint

class IngestaService:

    def __init__(self, db: Session):
        self.repo = IngestaRepository(db)

    # ── CRUD ──────────────────────────────────────────────

    def crear_fuente(self, dto: FuenteDatosCreateDTO) -> FuenteDatosResponseDTO:
        if self.repo.get_by_nombre(dto.nombre):
            raise IngestaError("source_exists", f"Ya existe una fuente con el nombre '{dto.nombre}'")

        data = dto.model_dump()
        data["endpoint"] = validate_source_endpoint(str(data["endpoint"]))
        data["api_key"] = encrypt_api_key(data.get("api_key"))

        fuente = FuenteDatos(**data)
        creada = self.repo.create(fuente)
        return FuenteDatosResponseDTO.model_validate(creada)

    def listar_fuentes(self) -> list[FuenteDatosResponseDTO]:
        return [FuenteDatosResponseDTO.model_validate(f) for f in self.repo.get_all()]

    def obtener_fuente(self, fuente_id: int) -> FuenteDatosResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise IngestaError("source_missing", "Fuente no encontrada")
        return FuenteDatosResponseDTO.model_validate(fuente)

    def actualizar_fuente(self, fuente_id: int, dto: FuenteDatosUpdateDTO) -> FuenteDatosResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise IngestaError("source_missing", "Fuente no encontrada")

        data = dto.model_dump(exclude_unset=True)
        # Preserve explicit api_key=null as a request to clear the credential,
        # while treating null for other optional update fields as omitted.
        data = {key: value for key, value in data.items() if value is not None or key == "api_key"}
        if "endpoint" in data:
            new_endpoint = validate_source_endpoint(str(data["endpoint"]))
            if endpoint_origin(new_endpoint) != endpoint_origin(fuente.endpoint) and "api_key" not in dto.model_fields_set:
                data["api_key"] = None
            data["endpoint"] = new_endpoint
        if "api_key" in data:
            data["api_key"] = encrypt_api_key(data["api_key"])

        actualizada = self.repo.update(fuente, data)
        return FuenteDatosResponseDTO.model_validate(actualizada)

    def eliminar_fuente(self, fuente_id: int) -> None:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise IngestaError("source_missing", "Fuente no encontrada")
        self.repo.delete(fuente)

    # ── Probar conexión ───────────────────────────────────

    def probar_conexion(self, fuente_id: int) -> ConexionTestResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise IngestaError("source_missing", "Fuente no encontrada")
        try:
            adapter = get_adapter(fuente.tipo,fuente.endpoint, fuente.api_key)
            datos = adapter.fetch(params={"$limit": 5})
            return ConexionTestResponseDTO(
                exitoso=True,
                mensaje="Conexión exitosa",
                registros_muestra=len(datos)
            )
        except Exception as exc:
            error_id = str(uuid.uuid4())
            logging.getLogger(__name__).error(
                "Fallo de prueba de conexión de fuente_id=%s; referencia=%s tipo=%s",
                fuente_id,
                error_id,
                type(exc).__name__,
            )
            return ConexionTestResponseDTO(
                exitoso=False,
                mensaje=f"No fue posible conectar con la fuente. Referencia: {error_id}"
            )

    # ── Sincronización ────────────────────────────────────

    def sincronizar_fuente(self, fuente_id: int, job_id: int | None = None) -> dict:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise IngestaError("source_missing", "Fuente no encontrada")

        if not self.repo.try_sync_lock(fuente_id):
            raise IngestaError("sync_locked", "La fuente ya se está sincronizando")

        historial = None
        total_traidos = 0
        total_insertados = 0
        try:
            historial = self.repo.crear_historial(fuente_id)
            checkpoint = (
                self.repo.get_sync_checkpoint(fuente_id, job_id)
                if job_id is not None
                else None
            )
            if checkpoint:
                fecha_desde = checkpoint["window_from"]
                fecha_hasta = checkpoint["window_to"]
                fecha_actualizacion_desde = checkpoint.get(
                    "updated_from",
                    fecha_desde,
                )
                cursor_id = checkpoint.get("last_id")
                filas_ventana = int(checkpoint.get("window_rows", 0))
            else:
                ultima_sync = fuente.ultima_sync
                fecha_desde = (
                    (
                        ultima_sync
                        - timedelta(hours=settings.INGESTA_OVERLAP_HOURS)
                    ).isoformat()
                    if ultima_sync
                    else "2020-01-01T00:00:00"
                )
                fecha_actualizacion_desde = (
                    ultima_sync.isoformat()
                    if ultima_sync
                    else "2020-01-01T00:00:00"
                )
                fecha_hasta = datetime.now(timezone.utc).isoformat()
                cursor_id = None
                filas_ventana = 0
                checkpoint = {
                    "fuente_id": fuente_id,
                    "window_from": fecha_desde,
                    "window_to": fecha_hasta,
                    "updated_from": fecha_actualizacion_desde,
                    "last_id": None,
                    "window_rows": 0,
                }

            adapter = get_adapter(fuente.tipo, fuente.endpoint, fuente.api_key)
            if (
                fuente.endpoint.endswith("/p6dx-8zbt.json")
                and callable(getattr(adapter, "probe_generation", None))
            ):
                has_local_rows, sample_ids = self.repo.local_generation_sample(fuente_id)
                previous_signature = checkpoint.get("source_signature")
                use_full_probe = (
                    previous_signature is None
                    or int(checkpoint.get("window_rows", 0)) % 1_000_000 == 0
                    or not callable(getattr(adapter, "probe_ids", None))
                )
                probe = (
                    adapter.probe_generation(sample_ids)
                    if use_full_probe else adapter.probe_ids(sample_ids)
                )
                signature = (
                    {key: probe[key] for key in ("filas", "min_actualizacion", "max_actualizacion")}
                    if use_full_probe else previous_signature
                )
                missing = probe["sample_missing"]
                checked = probe["sample_checked"]
                replaced = checked >= 5 and missing / checked >= 0.8
                changed_during_window = previous_signature is not None and previous_signature != signature
                unverifiable = has_local_rows and checked < 5 and previous_signature is None
                if replaced or changed_during_window or unverifiable:
                    reason = (
                        "La generación SECOP cambió; se requiere una recarga aislada reanudable."
                        if replaced else
                        "La fuente cambió durante la ventana; detenga y reconcilie el corte."
                        if changed_during_window else
                        "Los datos locales no tienen suficientes IDs Socrata para verificar la generación."
                    )
                    if job_id is not None:
                        self.repo.clear_sync_checkpoint(fuente_id, job_id)
                    self.repo.suspend_source_for_reconciliation(fuente_id)
                    self.repo.cerrar_historial(
                        historial.id, 0, 0, EstadoSync.PARCIAL, error=reason
                    )
                    return {
                        "historial_id": historial.id,
                        "registros_traidos": 0,
                        "registros_insertados": 0,
                        "fuente": fuente.nombre,
                        "parcial": True,
                        "replacement_detected": replaced,
                        "source_changed": changed_during_window,
                        "identity_unverifiable": unverifiable,
                        "source_paused": True,
                        "source_signature": signature,
                        "sample_checked": checked,
                        "sample_missing": missing,
                        "checkpoint": None,
                    }
                checkpoint["source_signature"] = signature

            if job_id is not None:
                self.repo.guardar_sync_checkpoint(fuente_id, job_id, checkpoint)

            registros_por_trabajo = 0
            limite = settings.INGESTA_MAX_RECORDS_PER_SYNC
            parcial = False
            lotes = adapter.fetch_todos(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                fecha_actualizacion_desde=fecha_actualizacion_desde,
                cursor_id=cursor_id,
            )
            try:
                for batch in lotes:
                    restantes = limite - registros_por_trabajo
                    lote = batch[:restantes]
                    if len(lote) < len(batch):
                        parcial = True

                    total_traidos += len(lote)
                    filas_ventana += len(lote)
                    checkpoint["window_rows"] = filas_ventana
                    if job_id is not None:
                        checkpoint["last_id"] = str(lote[-1][":id"])
                        insertados = self.repo.persistir_lote_y_checkpoint(
                            lote, fuente_id, job_id, checkpoint
                        )
                    else:
                        insertados = self.repo.insertar_raw_secop_bulk(lote, fuente_id)
                        if getattr(self.repo, "db", None) is not None:
                            self.repo.db.commit()
                    total_insertados += insertados
                    registros_por_trabajo += len(lote)

                    if parcial or registros_por_trabajo >= limite:
                        parcial = True
                        break
                    if not lote:
                        break
            finally:
                lotes.close()

            if (
                not parcial and total_traidos
                and fuente.endpoint.endswith("/p6dx-8zbt.json")
                and callable(getattr(adapter, "probe_generation", None))
            ):
                final_probe = adapter.probe_generation(sample_ids)
                final_signature = {
                    key: final_probe[key] for key in ("filas", "min_actualizacion", "max_actualizacion")
                }
                final_missing = final_probe["sample_missing"]
                final_checked = final_probe["sample_checked"]
                if final_signature != checkpoint["source_signature"] or (
                    final_checked >= 5 and final_missing / final_checked >= 0.8
                ):
                    if job_id is not None:
                        self.repo.clear_sync_checkpoint(fuente_id, job_id)
                    self.repo.suspend_source_for_reconciliation(fuente_id)
                    reason = "La generación SECOP cambió durante la carga; el watermark no avanzó."
                    self.repo.cerrar_historial(
                        historial.id, total_traidos, total_insertados, EstadoSync.PARCIAL,
                        error=reason,
                    )
                    return {
                        "historial_id": historial.id,
                        "registros_traidos": total_traidos,
                        "registros_insertados": total_insertados,
                        "fuente": fuente.nombre,
                        "parcial": True,
                        "replacement_detected": final_checked >= 5 and final_missing / final_checked >= 0.8,
                        "source_changed": final_signature != checkpoint["source_signature"],
                        "source_paused": True,
                        "source_signature": final_signature,
                        "sample_checked": final_checked,
                        "sample_missing": final_missing,
                        "checkpoint": None,
                    }

            if parcial:
                self.repo.cerrar_historial(
                    historial.id,
                    total_traidos,
                    total_insertados,
                    EstadoSync.PARCIAL,
                    error=(
                        f"Se alcanzó el límite de {limite} registros; "
                        "la siguiente sincronización continuará desde el cursor guardado."
                    ),
                )
            else:
                watermark = datetime.fromisoformat(fecha_hasta)
                self.repo.actualizar_ultima_sync(fuente_id, watermark, job_id=job_id)
                self.repo.cerrar_historial(
                    historial.id, total_traidos, total_insertados, EstadoSync.EXITOSO
                )

            return {
                "historial_id":          historial.id,
                "registros_traidos":     total_traidos,
                "registros_insertados":  total_insertados,
                "registros_duplicados":  total_traidos - total_insertados,
                "fuente":                fuente.nombre,
                "desde":                 fecha_desde,
                "hasta":                 fecha_hasta,
                "parcial":               parcial,
                "cursor":                checkpoint.get("last_id") if parcial else None,
                "checkpoint":            checkpoint if parcial else None,
            }

        except IngestaError as exc:
            db = getattr(self.repo, "db", None)
            if db is not None:
                db.rollback()
            if historial is not None:
                self.repo.cerrar_historial(
                    historial.id,
                    total_traidos,
                    total_insertados,
                    EstadoSync.ERROR,
                    error=exc.detail,
                )
            raise
        except Exception as exc:
            db = getattr(self.repo, "db", None)
            if db is not None:
                db.rollback()
            error_id = str(uuid.uuid4())
            logging.getLogger(__name__).error(
                "Fallo de sincronización de fuente_id=%s; referencia=%s tipo=%s",
                fuente_id,
                error_id,
                type(exc).__name__,
            )
            if historial is not None:
                self.repo.cerrar_historial(
                    historial.id,
                    total_traidos,
                    total_insertados,
                    EstadoSync.ERROR,
                    error=f"Error interno {error_id}",
                )
            raise IngestaError("sync_failed", f"Fallo en sincronización. Referencia: {error_id}") from exc
        finally:
            self.repo.release_sync_lock(fuente_id)

    def listar_historial(self, fuente_id: int = None) -> list[SincronizacionHistorialResponseDTO]:
        registros = self.repo.get_historial(fuente_id=fuente_id)
        resultado = []
        for r in registros:
            dto = SincronizacionHistorialResponseDTO.model_validate(r)
            fuente = self.repo.get_by_id(r.fuente_id)
            if fuente:
                dto.fuente_nombre = fuente.nombre
            resultado.append(dto)
        return resultado

    def resumen_historial(self) -> SincronizacionHistorialResumenDTO:
        return SincronizacionHistorialResumenDTO.model_validate(self.repo.resumen_historial())

    def listar_historial_pagina(
        self,
        page: int,
        size: int,
        fuente_id: int | None = None,
    ) -> SincronizacionHistorialPaginaDTO:
        if fuente_id is not None and not self.repo.get_by_id(fuente_id):
            raise IngestaError("source_missing", "Fuente no encontrada")
        registros, total = self.repo.get_historial_pagina(
            skip=(page - 1) * size,
            limit=size,
            fuente_id=fuente_id,
        )
        items = []
        for registro, fuente_nombre in registros:
            dto = SincronizacionHistorialResponseDTO.model_validate(registro)
            dto.fuente_nombre = fuente_nombre
            items.append(dto)
        return SincronizacionHistorialPaginaDTO(
            total=total,
            page=page,
            size=size,
            items=items,
        )

    def comparativa_fuentes(self) -> list[ComparativaFuenteDTO]:
        return [ComparativaFuenteDTO.model_validate(row) for row in self.repo.get_comparativa_fuentes()]

