import logging
import math
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from modules.analitica.dto.request import (
    OutlierCalculoRequest, OutlierFiltroRequest,
    DuplicadoCalculoRequest, DuplicadoFiltroRequest,
    AdjudicacionDirectaCalculoRequest, AdjudicacionDirectaFiltroRequest,
    RiesgoFiltroRequest, PesoActualizarRequest,
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
    ProveedorDirectaResumenResponse,
    ProveedorDirectaListaResponse,
    ProveedorDirectaDetalleResponse,
    PesoAnomaliaResponse,
    RiesgoProveedorResponse,
    RiesgoProveedorListaResponse,
    RiesgoGlobalResumenResponse,
    EjecucionAnaliticaEstadoResponse,
)
from modules.analitica.model.proveedor_adjudicacion_directa import ProveedorAdjudicacionDirecta
from modules.analitica.model.riesgo_proveedor import RiesgoProveedor
from modules.analitica.repository.repository import AnaliticaRepository

logger = logging.getLogger(__name__)


class FaltanEjecucionesAnaliticasError(ValueError):
    """Raised when a combined risk score would treat a missing input as zero."""


class EjecucionesAnaliticasIncompatiblesError(ValueError):
    """Raised when component runs do not describe the same current universe."""


class EjecucionAnaliticaNoEncontradaError(ValueError):
    """Raised when a query has no prior run to use as its default."""


class DatosInsuficientesAnaliticaError(ValueError):
    """Raised when the selected universe cannot support an analysis."""


class TipoAnomaliaNoEncontradoError(ValueError):
    """Raised when a requested anomaly weight does not exist."""


class FalloEjecucionAnaliticaError(RuntimeError):
    """Unexpected analysis failure carrying its server-side correlation ID."""

    def __init__(self, error_id: uuid.UUID):
        self.error_id = str(error_id)
        super().__init__("Fallo interno durante la ejecución analítica.")


def _scope_analitica(tipo: str, request) -> dict:
    if tipo == "RIESGO":
        return {}
    if tipo == "OUTLIERS":
        return {
            "fecha_campo": request.fecha_campo or "fecha_publicacion_normalizada",
            "fecha_desde": request.fecha_desde.isoformat() if request.fecha_desde else None,
            "fecha_hasta": request.fecha_hasta.isoformat() if request.fecha_hasta else None,
            "modalidad": request.modalidad,
        }
    return {
        "fecha_campo": "fecha_publicacion_normalizada",
        "fecha_desde": request.fecha_desde.isoformat() if request.fecha_desde else None,
        "fecha_hasta": request.fecha_hasta.isoformat() if request.fecha_hasta else None,
        "modalidad": None,
    }


def registrar_ejecucion_analitica(tipo: str, *, recibe_request: bool = True):
    """Persist run state even when analysis outputs no finding rows."""
    total_fields = {
        "OUTLIERS": "total_contratos_analizados",
        "DUPLICADOS": "total_duplicados",
        "ADJUDICACION_DIRECTA": "total_proveedores_detectados",
        "RIESGO": "total_proveedores_evaluados",
    }

    def decorar(funcion):
        @wraps(funcion)
        def ejecutar(self, *args, **kwargs):
            request = args[0] if recibe_request and args else None
            run_id = uuid.uuid4()
            parametros = request.model_dump(mode="json") if request is not None else {}
            universo = _scope_analitica(tipo, request)
            firma = self.repo.obtener_firma_universo()
            self.repo.iniciar_ejecucion_analitica(
                run_id=run_id,
                tipo=tipo,
                parametros=parametros,
                universo=universo,
                firma_universo=firma,
            )

            try:
                if recibe_request:
                    resultado = funcion(self, *args, _run_id=run_id, **kwargs)
                else:
                    resultado = funcion(self, _run_id=run_id, **kwargs)
                firma_final = self.repo.obtener_firma_universo()
                estado = "EXITOSO" if firma_final == firma else "DESACTUALIZADO"
                self.repo.finalizar_ejecucion_analitica(
                    run_id,
                    estado=estado,
                    total_resultados=int(getattr(resultado, total_fields[tipo], 0) or 0),
                )
                resultado.estado_ejecucion = estado
                return resultado
            except Exception as exc:
                self.db.rollback()
                error_id = uuid.uuid4()
                try:
                    self.repo.finalizar_ejecucion_analitica(
                        run_id,
                        estado="ERROR",
                        error_id=error_id,
                        mensaje_error=f"Error interno. Referencia: {error_id}",
                    )
                except Exception as registration_error:
                    self.db.rollback()
                    logger.error(
                        "No se pudo registrar el fallo analítico; referencia=%s tipo=%s",
                        error_id,
                        type(registration_error).__name__,
                    )
                logger.error(
                    "Falló la ejecución analítica; tipo=%s referencia=%s excepción=%s",
                    tipo,
                    error_id,
                    type(exc).__name__,
                )
                if isinstance(
                    exc,
                    (
                        FaltanEjecucionesAnaliticasError,
                        EjecucionesAnaliticasIncompatiblesError,
                        DatosInsuficientesAnaliticaError,
                    ),
                ):
                    raise
                raise FalloEjecucionAnaliticaError(error_id) from exc

        return ejecutar

    return decorar


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

    def obtener_estados_ultimas_ejecuciones(self) -> list[EjecucionAnaliticaEstadoResponse]:
        estados = []
        for tipo in ("OUTLIERS", "DUPLICADOS", "ADJUDICACION_DIRECTA", "RIESGO"):
            ejecucion = self.repo.obtener_ultima_ejecucion_analitica(tipo)
            if ejecucion is None:
                continue
            estados.append(EjecucionAnaliticaEstadoResponse(
                tipo=tipo,
                run_id=ejecucion.run_id,
                estado=self.repo.obtener_estado_ejecucion_analitica(ejecucion.run_id),
                fecha_inicio=ejecucion.fecha_inicio,
                fecha_fin=ejecucion.fecha_fin,
            ))
        return estados

    # ------------------------------------------------------------------
    # CASO DE USO PRINCIPAL
    # ------------------------------------------------------------------

    @registrar_ejecucion_analitica("OUTLIERS")
    def calcular_outliers(
        self, request: OutlierCalculoRequest, *, _run_id: UUID | None = None
    ) -> RunResumenResponse:
        """
        Ejecuta el análisis completo y persiste los resultados.
        Retorna el resumen de la ejecución.
        """
        run_id = _run_id or uuid.uuid4()
        campo = request.campo
        fecha_calculo = datetime.now(timezone.utc)

        # Validaciones de seguridad (allowlists)
        CAMPOS_NUMERICOS_VALIDOS = {"valor_total_normalizado", "precio_base_normalizado", "nivel_confianza", "cantidad_campos_faltantes"}
        CAMPOS_FECHA_VALIDOS = {"fecha_publicacion_normalizada", "fecha_adjudicacion_normalizada"}

        if campo not in CAMPOS_NUMERICOS_VALIDOS:
            raise ValueError(f"Campo numérico a analizar no es válido: {campo}")

        if request.fecha_campo and request.fecha_campo not in CAMPOS_FECHA_VALIDOS:
            raise ValueError(f"Campo de fecha para filtrar no es válido: {request.fecha_campo}")

        logger.info(
            f"[Outliers Analysis] Iniciando ejecución {run_id}. "
            f"Campo: '{campo}'. Fecha Campo: '{request.fecha_campo}'. "
            f"Rango: {request.fecha_desde} - {request.fecha_hasta}. "
            f"Modalidad: '{request.modalidad}'"
        )
        start_time = datetime.now(timezone.utc)

        # PASO 1: calcular Q1, Q3, IQR y límites por grupo en PostgreSQL
        estadisticas_por_grupo: dict[str, dict] = {
            fila["grupo"]: fila
            for fila in self.repo.obtener_estadisticas_por_grupo(
                campo=campo,
                fecha_campo=request.fecha_campo,
                fecha_desde=request.fecha_desde,
                fecha_hasta=request.fecha_hasta,
                modalidad=request.modalidad,
            )
        }

        if not estadisticas_por_grupo:
            raise DatosInsuficientesAnaliticaError(
                "No se encontraron contratos válidos con los filtros indicados "
                "o ningún grupo tiene varianza suficiente para calcular IQR."
            )

        # Clasificar e insertar en la base, evitando materializar millones de filas.
        total_analizados, total_outliers = self.repo.guardar_resultados_outliers_sql(
            run_id=run_id,
            campo=campo,
            estadisticas_por_grupo=estadisticas_por_grupo,
            fecha_calculo=fecha_calculo,
            fecha_campo=request.fecha_campo,
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
            modalidad=request.modalidad,
        )
        self.db.commit()

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"[Outliers Analysis] Finalizada ejecución {run_id} en {duration:.2f}s. "
            f"Contratos analizados: {total_analizados}. Outliers detectados: {total_outliers}."
        )

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
            fecha_calculo=resumen.get("fecha_calculo", datetime.now(timezone.utc)),
            estado_ejecucion=self.repo.obtener_estado_ejecucion_analitica(run_id),
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
            raise EjecucionAnaliticaNoEncontradaError(
                "No existe ninguna ejecución de análisis. Ejecuta el cálculo primero."
            )
        return ultimo

    # ------------------------------------------------------------------
    # ANÁLISIS DE DUPLICADOS EN PERÍODO CORTO
    # ------------------------------------------------------------------

    @registrar_ejecucion_analitica("DUPLICADOS")
    def calcular_duplicados(
        self, request: DuplicadoCalculoRequest, *, _run_id: UUID | None = None
    ) -> DuplicadoResumenResponse:
        run_id = _run_id or uuid.uuid4()
        fecha_calculo = datetime.now(timezone.utc)

        self.repo.guardar_duplicados_sql(
            run_id=run_id,
            fecha_calculo=fecha_calculo,
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
        )
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
            fecha_calculo=(resumen.get("fecha_calculo") if resumen else None) or datetime.now(timezone.utc),
            estado_ejecucion=self.repo.obtener_estado_ejecucion_analitica(run_id),
        )

    def _resolver_run_id_duplicados(self, run_id_str: Optional[str]) -> UUID:
        if run_id_str:
            return UUID(run_id_str)
        ultimo = self.repo.obtener_ultimo_run_id_duplicados()
        if not ultimo:
            raise EjecucionAnaliticaNoEncontradaError(
                "No existe ninguna ejecución de análisis de duplicados. Ejecuta el cálculo primero."
            )
        return ultimo

    # ------------------------------------------------------------------
    # ANÁLISIS DE ABUSO DE ADJUDICACIÓN DIRECTA
    # ------------------------------------------------------------------

    @registrar_ejecucion_analitica("ADJUDICACION_DIRECTA")
    def calcular_abuso_adjudicacion_directa(
        self, request: AdjudicacionDirectaCalculoRequest, *, _run_id: UUID | None = None
    ) -> ProveedorDirectaResumenResponse:
        """
        Detecta proveedores con abuso de adjudicación directa.
        Flujo:
            1. Ejecutar CTE en PostgreSQL — agrupación por proveedor
            2. Calcular score y clasificación de riesgo
            3. Persistir en proveedor_adjudicacion_directa
            4. Retornar resumen
        """
        run_id = _run_id or uuid.uuid4()
        fecha_calculo = datetime.now(timezone.utc)

        logger.info(f"Iniciando cálculo de abuso de adjudicación directa. Run ID: {run_id}")
        logger.info(f"Parámetros: minimo_directas={request.minimo_directas}, dias_ventana={request.dias_ventana}")

        filas = self.repo.calcular_adjudicaciones_directas(
            fecha_desde=request.fecha_desde,
            fecha_hasta=request.fecha_hasta,
            minimo_directas=request.minimo_directas,
            dias_ventana=request.dias_ventana,
        )

        logger.info(f"Proveedores potenciales detectados por el repositorio: {len(filas)}")

        registros: list[ProveedorAdjudicacionDirecta] = []

        for fila in filas:
            porcentaje = float(fila["porcentaje_directos"] or 0)

            # Score: porcentaje / 10  (rango 0.0 – 10.0)
            score = round(porcentaje / 10, 2)

            # Clasificación de riesgo
            if porcentaje >= 90:
                clasificacion = "ALTO"
            elif porcentaje >= 70:
                clasificacion = "MEDIO"
            else:
                clasificacion = "BAJO"

            registros.append(
                ProveedorAdjudicacionDirecta(
                    run_id=run_id,
                    contrato_id=fila.get("contrato_id"),
                    proveedor=fila["proveedor"],
                    nit_proveedor=fila.get("nit_proveedor"),
                    entidad=fila.get("entidad"),
                    tipo_contrato=fila.get("tipo_contrato"),
                    modalidad_contratacion=fila.get("modalidad_contratacion"),
                    fecha_contrato=fila.get("fecha_contrato"),
                    total_contratos=int(fila["total_contratos"]),
                    contratos_directos=int(fila["contratos_directos"]),
                    porcentaje_directos=porcentaje,
                    score_riesgo=score,
                    clasificacion_riesgo=clasificacion,
                    fecha_calculo=fecha_calculo,
                )
            )

        if registros:
            logger.info(f"Guardando {len(registros)} hallazgos en la base de datos.")
            self.repo.guardar_adjudicaciones_directas(registros)
            self.db.commit()
        else:
            logger.warning("No se encontraron proveedores que cumplan con los criterios de abuso.")

        return self.obtener_resumen_directas(run_id)

    def listar_directas(
        self, filtros: AdjudicacionDirectaFiltroRequest
    ) -> ProveedorDirectaListaResponse:
        """
        Lista proveedores con abuso de adjudicación directa con filtros y paginación.
        Si no se pasa run_id, usa el de la última ejecución.
        """
        run_id = self._resolver_run_id_directas(filtros.run_id)

        items, total = self.repo.obtener_proveedores_directas(
            run_id=run_id,
            riesgo=filtros.riesgo,
            score_minimo=filtros.score_minimo,
            score_maximo=filtros.score_maximo,
            porcentaje_minimo=filtros.porcentaje_minimo,
            porcentaje_maximo=filtros.porcentaje_maximo,
            solo_abuso_directas=filtros.solo_abuso_directas,
            page=filtros.page,
            page_size=filtros.page_size,
        )

        total_pages = math.ceil(total / filtros.page_size) if total > 0 else 0

        return ProveedorDirectaListaResponse(
            items=[ProveedorDirectaDetalleResponse.model_validate(item) for item in items],
            total=total,
            page=filtros.page,
            page_size=filtros.page_size,
            total_pages=total_pages,
        )

    def obtener_resumen_directas(
        self, run_id: UUID
    ) -> ProveedorDirectaResumenResponse:
        """Construye el resumen de una ejecución de adjudicación directa."""
        data = self.repo.obtener_resumen_directas(run_id)
        resumen = data["resumen"]
        por_riesgo = data["por_riesgo"]

        return ProveedorDirectaResumenResponse(
            run_id=run_id,
            total_proveedores_detectados=resumen.get("total_proveedores_detectados", 0) if resumen else 0,
            promedio_porcentaje_directos=round(
                float(resumen.get("promedio_porcentaje_directos", 0.0) or 0), 2
            ) if resumen else 0.0,
            promedio_score=round(
                float(resumen.get("promedio_score", 0.0) or 0), 2
            ) if resumen else 0.0,
            resumen_por_riesgo=[RiesgoResumenResponse(**r) for r in por_riesgo],
            fecha_calculo=resumen.get("fecha_calculo", datetime.now(timezone.utc)) if resumen else datetime.now(timezone.utc),
            estado_ejecucion=self.repo.obtener_estado_ejecucion_analitica(run_id),
        )

    def _resolver_run_id_directas(self, run_id_str: Optional[str]) -> UUID:
        if run_id_str:
            return UUID(run_id_str)
        ultimo = self.repo.obtener_ultimo_run_id_directas()
        if not ultimo:
            raise EjecucionAnaliticaNoEncontradaError(
                "No existe ninguna ejecución de análisis de directas. "
                "Ejecuta el cálculo primero."
            )
        return ultimo

    # ------------------------------------------------------------------
    # RIESGO COMBINADO Y PESOS
    # ------------------------------------------------------------------

    def obtener_pesos(self) -> list[PesoAnomaliaResponse]:
        pesos = self.repo.obtener_pesos()
        return [PesoAnomaliaResponse.model_validate(p) for p in pesos]

    def actualizar_peso(self, tipo_anomalia: str, request: PesoActualizarRequest) -> PesoAnomaliaResponse:
        obj = self.repo.actualizar_peso(tipo_anomalia.upper(), request.peso)
        if not obj:
            raise TipoAnomaliaNoEncontradoError(
                f"Tipo de anomalía '{tipo_anomalia}' no encontrado."
            )
        return PesoAnomaliaResponse.model_validate(obj)

    @registrar_ejecucion_analitica("RIESGO", recibe_request=False)
    def calcular_riesgo_global(self, *, _run_id: UUID | None = None) -> RiesgoGlobalResumenResponse:
        run_id = _run_id or uuid.uuid4()
        fecha_calculo = datetime.now(timezone.utc)

        # 1. Obtener pesos actuales
        pesos_db = self.repo.obtener_pesos()
        pesos_dict = {p.tipo_anomalia: float(p.peso) for p in pesos_db}
        peso_outlier = pesos_dict.get("OUTLIER", 1.0)
        peso_duplicado = pesos_dict.get("DUPLICADO_CORTO", 1.5)
        peso_directo = pesos_dict.get("ABUSO_DIRECTO", 2.0)

        # 2. Require all component runs. A missing analysis is not evidence of
        # zero risk and must never be silently converted to a BAJO classification.
        ejecuciones = self.repo.obtener_ejecuciones_componentes_riesgo()
        faltantes = [nombre for nombre, ejecucion in ejecuciones.items() if ejecucion is None]
        if faltantes:
            nombres = ", ".join(faltantes)
            raise FaltanEjecucionesAnaliticasError(
                f"No se puede calcular el riesgo combinado: faltan ejecuciones de {nombres}."
            )
        ejecuciones = {nombre: ejecucion for nombre, ejecucion in ejecuciones.items() if ejecucion is not None}
        no_exitosas = [nombre for nombre, ejecucion in ejecuciones.items() if ejecucion.estado != "EXITOSO"]
        if no_exitosas:
            raise FaltanEjecucionesAnaliticasError(
                "La última ejecución no fue exitosa para: " + ", ".join(no_exitosas) + "."
            )

        alcances = [ejecucion.universo for ejecucion in ejecuciones.values()]
        firmas = [ejecucion.firma_universo for ejecucion in ejecuciones.values()]
        alcance_outliers = ejecuciones["outliers"].universo
        if (
            len({str(sorted(scope.items())) for scope in alcances}) != 1
            or alcance_outliers.get("fecha_campo") != "fecha_publicacion_normalizada"
            or alcance_outliers.get("modalidad") is not None
            or len({str(sorted(firma.items())) for firma in firmas}) != 1
            or self.repo.obtener_firma_universo() != firmas[0]
        ):
            raise EjecucionesAnaliticasIncompatiblesError(
                "Las últimas ejecuciones analíticas no comparten el mismo universo vigente. Reejecuta los módulos con filtros de publicación compatibles."
            )

        run_ids = {nombre: ejecucion.run_id for nombre, ejecucion in ejecuciones.items()}
        self.repo.actualizar_contexto_ejecucion(
            run_id,
            parametros={
                "run_ids_componentes": {nombre: str(value) for nombre, value in run_ids.items()},
                "pesos": pesos_dict,
            },
            universo=alcances[0],
        )
        scores = self.repo.obtener_scores_combinados_por_proveedor(run_ids)
        pesos_con_ejecuciones = {
            **pesos_dict,
            "run_ids": {nombre: str(component_run_id) for nombre, component_run_id in run_ids.items()},
        }

        registros = []
        for fila in scores:
            outlier_val = float(fila.get("max_score_outlier") or 0.0)
            dup_val = float(fila.get("max_score_duplicado") or 0.0)
            dir_val = float(fila.get("score_directo") or 0.0)

            score_final = (outlier_val * peso_outlier) + (dup_val * peso_duplicado) + (dir_val * peso_directo)

            # Clasificación simple:
            if score_final >= 5.0:
                riesgo = "ALTO"
            elif score_final >= 2.0:
                riesgo = "MEDIO"
            else:
                riesgo = "BAJO"

            registros.append(
                RiesgoProveedor(
                    run_id=run_id,
                    proveedor=fila["proveedor"],
                    nit_proveedor=fila["nit_proveedor"],
                    max_score_outlier=outlier_val,
                    max_score_duplicado=dup_val,
                    score_directo=dir_val,
                    score_final=round(score_final, 2),
                    clasificacion_riesgo=riesgo,
                    pesos_aplicados=pesos_con_ejecuciones,
                    fecha_calculo=fecha_calculo
                )
            )

        if registros:
            self.repo.guardar_riesgo_proveedores(registros)
        self.db.commit()

        return self.obtener_resumen_riesgo(run_id)

    def listar_riesgos(self, filtros: RiesgoFiltroRequest) -> RiesgoProveedorListaResponse:
        run_id = self._resolver_run_id_riesgo(filtros.run_id)

        items, total = self.repo.obtener_riesgos(
            run_id=run_id,
            proveedor=filtros.proveedor,
            riesgo=filtros.riesgo,
            score_minimo=filtros.score_minimo,
            page=filtros.page,
            page_size=filtros.page_size,
        )

        total_pages = math.ceil(total / filtros.page_size) if total > 0 else 0

        return RiesgoProveedorListaResponse(
            items=[RiesgoProveedorResponse.model_validate(item) for item in items],
            total=total,
            page=filtros.page,
            page_size=filtros.page_size,
            total_pages=total_pages,
        )

    def obtener_resumen_riesgo(self, run_id: UUID) -> RiesgoGlobalResumenResponse:
        data = self.repo.obtener_resumen_riesgo(run_id)
        resumen = data["resumen"]
        por_riesgo = data["por_riesgo"]

        return RiesgoGlobalResumenResponse(
            run_id=run_id,
            total_proveedores_evaluados=resumen.get("total_proveedores_evaluados", 0) if resumen else 0,
            promedio_score_final=round(float(resumen.get("promedio_score_final", 0.0) or 0), 2) if resumen else 0.0,
            resumen_por_riesgo=[RiesgoResumenResponse(**r) for r in por_riesgo],
            fecha_calculo=resumen.get("fecha_calculo", datetime.now(timezone.utc)) if resumen else datetime.now(timezone.utc),
            estado_ejecucion=self.repo.obtener_estado_ejecucion_analitica(run_id),
        )

    def _resolver_run_id_riesgo(self, run_id_str: Optional[str]) -> UUID:
        if run_id_str:
            return UUID(run_id_str)
        ultimo = self.repo.obtener_ultimo_run_id_riesgo()
        if not ultimo:
            raise EjecucionAnaliticaNoEncontradaError(
                "No existe ninguna ejecución de riesgo consolidado. Ejecuta el cálculo primero."
            )
        return ultimo
