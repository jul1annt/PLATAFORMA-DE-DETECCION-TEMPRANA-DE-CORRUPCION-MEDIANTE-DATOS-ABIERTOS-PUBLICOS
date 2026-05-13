import math
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from modules.analitica.dto.request import (
    OutlierCalculoRequest, OutlierFiltroRequest,
    DuplicadoCalculoRequest, DuplicadoFiltroRequest
)
from modules.analitica.dto.response import (
    RunResumenResponse,
    OutlierListaResponse,
    OutlierDetalleResponse,
    EstadisticasGrupoResponse,
    DuplicadoResumenResponse,
    DuplicadoListaResponse,
    DuplicadoDetalleResponse,
    RiesgoResumenResponse,
)
from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo
from modules.analitica.repository.repository import AnaliticaRepository


class AnaliticaService:
    """
    Orquesta el análisis IQR de outliers sobre contratos_procesados.

    Flujo principal (calcular_outliers):
        1. Obtener estadísticas por grupo (Q1, Q3, IQR, límites) vía SQL
        2. Obtener contratos válidos del mismo universo
        3. Clasificar cada contrato contra los límites de su grupo
        4. Calcular score de extremidad
        5. Persistir resultados en contrato_outlier
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = AnaliticaRepository(db)

    # ------------------------------------------------------------------
    # CASO DE USO PRINCIPAL
    # ------------------------------------------------------------------

    def calcular_outliers(self, request: OutlierCalculoRequest) -> RunResumenResponse:
        """
        Ejecuta el análisis completo y persiste los resultados.
        Retorna el resumen de la ejecución.
        """
        run_id = uuid.uuid4()
        campo = request.campo_analizado
        fecha_calculo = datetime.utcnow()

        # PASO 1: calcular Q1, Q3, IQR y límites por grupo en PostgreSQL
        estadisticas_por_grupo: dict[str, dict] = {
            fila["grupo"]: fila
            for fila in self.repo.obtener_estadisticas_por_grupo(
                campo=campo,
                fecha_desde=request.fecha_desde,
                fecha_hasta=request.fecha_hasta,
                modalidades=request.modalidades,
            )
        }

        if not estadisticas_por_grupo:
            raise ValueError(
                "No se encontraron contratos válidos con los filtros indicados "
                "o ningún grupo tiene varianza suficiente para calcular IQR."
            )

        # PASO 2: traer los contratos válidos del mismo universo
        contratos = self.repo.obtener_contratos_validos(
            campo=campo,
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
            modalidades=request.modalidades,
        )

        # PASO 3 y 4: clasificar y calcular score
        registros: list[ContratoOutlier] = []

        for contrato in contratos:
            grupo = contrato["grupo"]

            # Si el grupo del contrato no tiene estadísticas (IQR=0, grupo sin varianza),
            # se omite del análisis — no se puede clasificar sin referencia estadística.
            if not grupo or grupo not in estadisticas_por_grupo:
                continue

            stats = estadisticas_por_grupo[grupo]
            valor = float(contrato["valor"])
            limite_inf = float(stats["limite_inferior"])
            limite_sup = float(stats["limite_superior"])
            iqr = float(stats["iqr"])

            es_outlier, direccion, score = self._clasificar(
                valor, limite_inf, limite_sup, iqr
            )

            registros.append(
                ContratoOutlier(
                    contrato_id=contrato["id"],
                    run_id=run_id,
                    grupo=grupo,
                    campo_analizado=campo,
                    valor=valor,
                    q1=float(stats["q1"]),
                    q3=float(stats["q3"]),
                    iqr=iqr,
                    limite_inferior=limite_inf,
                    limite_superior=limite_sup,
                    es_outlier=es_outlier,
                    direccion_outlier=direccion,
                    score=round(score, 4),
                    fecha_calculo=fecha_calculo,
                )
            )

        # PASO 5: persistir
        self.repo.guardar_resultados(registros)
        self.db.commit()

        return self.obtener_resumen(run_id)

    # ------------------------------------------------------------------
    # CONSULTAS
    # ------------------------------------------------------------------

    def listar_outliers(self, filtros: OutlierFiltroRequest) -> OutlierListaResponse:
        """
        Lista contratos analizados con filtros opcionales y paginación.
        Si no se pasa run_id, usa el de la última ejecución.
        """
        run_id = self._resolver_run_id(filtros.run_id)

        items, total = self.repo.obtener_outliers(
            run_id=run_id,
            solo_outliers=filtros.solo_outliers,
            grupo=filtros.grupo,
            direccion=filtros.direccion,
            score_minimo=filtros.score_minimo,
            page=filtros.page,
            page_size=filtros.page_size,
        )

        total_pages = math.ceil(total / filtros.page_size) if total > 0 else 0

        return OutlierListaResponse(
            items=[OutlierDetalleResponse.model_validate(item) for item in items],
            total=total,
            page=filtros.page,
            page_size=filtros.page_size,
            total_pages=total_pages,
        )

    def obtener_resumen(self, run_id: UUID) -> RunResumenResponse:
        """
        Construye el resumen de una ejecución: totales, por grupo, porcentajes.
        Es lo que consume el dashboard.
        """
        data = self.repo.obtener_resumen_run(run_id)
        resumen = data["resumen"]
        por_grupo = data["por_grupo"]

        total_analizados = resumen.get("total_analizados", 0)
        total_outliers = resumen.get("total_outliers", 0)
        porcentaje = round((total_outliers / total_analizados * 100), 2) if total_analizados > 0 else 0.0

        return RunResumenResponse(
            run_id=run_id,
            campo_analizado=resumen.get("campo_analizado", ""),
            total_contratos_analizados=total_analizados,
            total_outliers=total_outliers,
            porcentaje_outliers=porcentaje,
            total_outliers_alto=resumen.get("total_alto", 0),
            total_outliers_bajo=resumen.get("total_bajo", 0),
            grupos_procesados=resumen.get("grupos_procesados", 0),
            estadisticas_por_grupo=[
                EstadisticasGrupoResponse(**grupo) for grupo in por_grupo
            ],
            fecha_calculo=resumen.get("fecha_calculo", datetime.utcnow()),
        )

    # ------------------------------------------------------------------
    # LÓGICA DE CLASIFICACIÓN (pura, testeable sin BD)
    # ------------------------------------------------------------------

    @staticmethod
    def _clasificar(
        valor: float,
        limite_inferior: float,
        limite_superior: float,
        iqr: float,
    ) -> tuple[bool, Optional[str], float]:
        """
        Clasifica un valor respecto a los límites IQR de su grupo.

        Retorna (es_outlier, direccion, score).

        Score:
            - Outlier alto:  (valor - limite_superior) / IQR
            - Outlier bajo:  (limite_inferior - valor) / IQR
            - No outlier:    0.0

        Interpretación del score:
            0.0 - 1.0  → ligeramente fuera del rango (borderline)
            1.0 - 3.0  → moderadamente atípico
            > 3.0      → extremadamente atípico
        """
        if valor > limite_superior:
            score = (valor - limite_superior) / iqr
            return True, "ALTO", score

        if valor < limite_inferior:
            score = (limite_inferior - valor) / iqr
            return True, "BAJO", score

        return False, None, 0.0

    def _resolver_run_id(self, run_id_str: Optional[str]) -> UUID:
        if run_id_str:
            return UUID(run_id_str)
        ultimo = self.repo.obtener_ultimo_run_id()
        if not ultimo:
            raise ValueError("No existe ninguna ejecución de análisis. Ejecuta el cálculo primero.")
        return ultimo

    # ------------------------------------------------------------------
    # ANÁLISIS DE DUPLICADOS EN PERÍODO CORTO
    # ------------------------------------------------------------------

    def calcular_duplicados(self, request: DuplicadoCalculoRequest) -> DuplicadoResumenResponse:
        run_id = uuid.uuid4()
        fecha_calculo = datetime.utcnow()

        pares_duplicados = self.repo.obtener_pares_duplicados(
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
        )

        registros: list[ContratoDuplicadoPeriodo] = []

        for par in pares_duplicados:
            dias = int(par["diferencia_dias"])
            
            # Cálculo del score
            # Máximo score (10.0) si diferencia es 0 días. Va bajando a 0.0 si es 30 días.
            score = max(0.0, 10.0 - (dias * (10.0 / 30.0)))
            
            # Clasificación de riesgo
            if dias <= 5:
                riesgo = "ALTO"
            elif dias <= 15:
                riesgo = "MEDIO"
            else:
                riesgo = "BAJO"

            registros.append(
                ContratoDuplicadoPeriodo(
                    run_id=run_id,
                    contrato_id=par["contrato_id"],
                    contrato_relacionado_id=par["contrato_relacionado_id"],
                    proveedor=par["proveedor"],
                    entidad=par["entidad"],
                    tipo_contrato=par["tipo_contrato"],
                    modalidad_contratacion=par["modalidad_contratacion"],
                    fecha_contrato=par["fecha_contrato"],
                    fecha_relacionada=par["fecha_relacionada"],
                    diferencia_dias=dias,
                    duplicado_score=round(score, 2),
                    clasificacion_riesgo=riesgo,
                    fecha_calculo=fecha_calculo,
                )
            )

        if registros:
            self.repo.guardar_duplicados(registros)
            self.db.commit()

        return self.obtener_resumen_duplicados(run_id)

    def listar_duplicados(self, filtros: DuplicadoFiltroRequest) -> DuplicadoListaResponse:
        run_id = self._resolver_run_id_duplicados(filtros.run_id)

        items, total = self.repo.obtener_duplicados_periodo(
            run_id=run_id,
            riesgo=filtros.riesgo,
            score_minimo=filtros.score_minimo,
            page=filtros.page,
            page_size=filtros.page_size,
        )

        total_pages = math.ceil(total / filtros.page_size) if total > 0 else 0

        return DuplicadoListaResponse(
            items=[DuplicadoDetalleResponse.model_validate(item) for item in items],
            total=total,
            page=filtros.page,
            page_size=filtros.page_size,
            total_pages=total_pages,
        )

    def obtener_resumen_duplicados(self, run_id: UUID) -> DuplicadoResumenResponse:
        data = self.repo.obtener_resumen_duplicados_run(run_id)
        resumen = data["resumen"]
        por_riesgo = data["por_riesgo"]

        return DuplicadoResumenResponse(
            run_id=run_id,
            total_duplicados=resumen.get("total_duplicados", 0) if resumen else 0,
            promedio_dias_diferencia=round(float(resumen.get("promedio_dias_diferencia", 0.0) or 0), 2) if resumen else 0.0,
            promedio_score=round(float(resumen.get("promedio_score", 0.0) or 0), 2) if resumen else 0.0,
            resumen_por_riesgo=[RiesgoResumenResponse(**r) for r in por_riesgo],
            fecha_calculo=resumen.get("fecha_calculo", datetime.utcnow()) if resumen else datetime.utcnow(),
        )

    def _resolver_run_id_duplicados(self, run_id_str: Optional[str]) -> UUID:
        if run_id_str:
            return UUID(run_id_str)
        ultimo = self.repo.obtener_ultimo_run_id_duplicados()
        if not ultimo:
            raise ValueError("No existe ninguna ejecución de análisis de duplicados. Ejecuta el cálculo primero.")
        return ultimo