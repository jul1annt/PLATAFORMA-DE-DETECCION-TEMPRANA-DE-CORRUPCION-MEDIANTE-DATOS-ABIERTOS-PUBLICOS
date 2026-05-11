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
        fuente = FuenteDatos(**dto.model_dump())
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
        actualizada = self.repo.update(fuente, dto.model_dump(exclude_none=True))
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
            adapter = get_adapter(fuente.tipo, fuente.api_key)
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
            adapter = get_adapter(fuente.tipo, fuente.api_key)
            datos = adapter.fetch()
            # Aquí se persisten los datos crudos (RawData - lo definimos en la siguiente HU)
            self.repo.actualizar_ultima_sync(fuente_id, datetime.now(timezone.utc))
            return {"registros_traidos": len(datos), "fuente": fuente.nombre}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Fallo en sincronización: {str(e)}")