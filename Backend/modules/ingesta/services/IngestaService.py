from sqlalchemy.orm import Session
from datetime import datetime, timezone
from fastapi import HTTPException, status

from ..repository.IngestaRepository import IngestaRepository
from ..adapters.adapter_factory import get_adapter
from ..dto.request import FuenteDatosCreateDTO, FuenteDatosUpdateDTO
from ..dto.response import FuenteDatosResponseDTO, ConexionTestResponseDTO
from ..model.FuenteDatos import FuenteDatos

class IngestaService:

    def __init__(self, db: Session):
        self.repo = IngestaRepository(db)

    # ── CRUD ──────────────────────────────────────────────

    def crear_fuente(self, dto: FuenteDatosCreateDTO) -> FuenteDatosResponseDTO:
        if self.repo.get_by_nombre(dto.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una fuente con el nombre '{dto.nombre}'"
            )

        data = dto.model_dump()
        data["endpoint"] = str(data["endpoint"])   # <-- fix

        fuente = FuenteDatos(**data)
        creada = self.repo.create(fuente)
        return FuenteDatosResponseDTO.model_validate(creada)

    def listar_fuentes(self) -> list[FuenteDatosResponseDTO]:
        return [FuenteDatosResponseDTO.model_validate(f) for f in self.repo.get_all()]

    def obtener_fuente(self, fuente_id: int) -> FuenteDatosResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")
        return FuenteDatosResponseDTO.model_validate(fuente)

    def actualizar_fuente(self, fuente_id: int, dto: FuenteDatosUpdateDTO) -> FuenteDatosResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")

        data = dto.model_dump(exclude_none=True)
        if "endpoint" in data:
            data["endpoint"] = str(data["endpoint"])   # <-- fix

        actualizada = self.repo.update(fuente, data)
        return FuenteDatosResponseDTO.model_validate(actualizada)

    def eliminar_fuente(self, fuente_id: int) -> None:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")
        self.repo.delete(fuente)

    # ── Probar conexión ───────────────────────────────────

    def probar_conexion(self, fuente_id: int) -> ConexionTestResponseDTO:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")
        try:
            adapter = get_adapter(fuente.tipo,fuente.endpoint, fuente.api_key)
            datos = adapter.fetch(params={"$limit": 5})
            return ConexionTestResponseDTO(
                exitoso=True,
                mensaje="Conexión exitosa",
                registros_muestra=len(datos)
            )
        except Exception as e:
            return ConexionTestResponseDTO(
                exitoso=False,
                mensaje=f"Error al conectar: {str(e)}"
            )

    # ── Sincronización ────────────────────────────────────

    def sincronizar_fuente(self, fuente_id: int) -> dict:
        fuente = self.repo.get_by_id(fuente_id)
        if not fuente:
            raise HTTPException(status_code=404, detail="Fuente no encontrada")
        try:
            adapter = get_adapter(fuente.tipo, fuente.endpoint, fuente.api_key)

            fecha_desde = None
            if fuente.ultima_sync:
                fecha_desde = fuente.ultima_sync.strftime("%Y-%m-%d")

            total_traidos   = 0
            total_insertados = 0

            # Itera batch por batch sin cargar todo en memoria
            for batch in adapter.fetch_todos(fecha_desde=fecha_desde):
                insertados = self.repo.insertar_raw_secop_bulk(batch, fuente_id)
                total_traidos    += len(batch)
                total_insertados += insertados
                print(f"[SYNC] traidos={total_traidos} | insertados={total_insertados}")

            self.repo.actualizar_ultima_sync(fuente_id, datetime.now(timezone.utc))

            return {
                "registros_traidos":     total_traidos,
                "registros_insertados":  total_insertados,
                "registros_duplicados":  total_traidos - total_insertados,
                "fuente":  fuente.nombre,
                "desde":   fecha_desde or "2020-01-01",
                "hasta":   datetime.today().strftime("%Y-%m-%d")
            }
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Fallo en sincronización: {str(e)}")