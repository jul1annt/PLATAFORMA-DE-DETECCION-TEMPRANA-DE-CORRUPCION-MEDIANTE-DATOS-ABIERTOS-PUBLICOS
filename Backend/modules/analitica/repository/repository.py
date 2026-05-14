from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo
from modules.analitica.model.proveedor_adjudicacion_directa import ProveedorAdjudicacionDirecta



class AnaliticaRepository:

    def __init__(self, db: Session):
        self.db = db

    def obtener_estadisticas_por_grupo(
        self,
        campo: str,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        modalidades: Optional[list[str]] = None,
    ) -> list[dict]:
        filtros_base = self._construir_filtros_base(campo, fecha_desde, fecha_hasta, modalidades)

        query = text(f"""
            WITH contratos_validos AS (
                SELECT
                    COALESCE(
                        NULLIF(TRIM(modalidad_contratacion), ''),
                        NULLIF(TRIM(tipo_contrato_normalizado), '')
                    ) AS grupo,
                    {campo} AS valor
                FROM contratos_procesados
                WHERE es_incompleto = false
                  AND {campo} IS NOT NULL
                  AND {campo} > 0
                  {filtros_base['where_extra']}
            ),
            estadisticas AS (
                SELECT
                    grupo,
                    COUNT(*)                                                          AS total_contratos,
                    percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)               AS q1,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)               AS q3,
                    percentile_cont(0.75) WITHIN GROUP (ORDER BY valor)
                        - percentile_cont(0.25) WITHIN GROUP (ORDER BY valor)         AS iqr
                FROM contratos_validos
                WHERE grupo IS NOT NULL
                GROUP BY grupo
            )
            SELECT
                grupo,
                total_contratos,
                q1,
                q3,
                iqr,
                q1 - (1.5 * iqr) AS limite_inferior,
                q3 + (1.5 * iqr) AS limite_superior
            FROM estadisticas
            WHERE iqr > 0
        """)

        resultado = self.db.execute(query, filtros_base["params"])
        return [dict(row._mapping) for row in resultado]

    def obtener_contratos_validos(
        self,
        campo: str,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        modalidades: Optional[list[str]] = None,
    ) -> list[dict]:
        filtros_base = self._construir_filtros_base(campo, fecha_desde, fecha_hasta, modalidades)

        query = text(f"""
            SELECT
                id,
                {campo} AS valor,
                COALESCE(
                    NULLIF(TRIM(modalidad_contratacion), ''),
                    NULLIF(TRIM(tipo_contrato_normalizado), '')
                ) AS grupo
            FROM contratos_procesados
            WHERE es_incompleto = false
              AND {campo} IS NOT NULL
              AND {campo} > 0
              {filtros_base['where_extra']}
        """)

        resultado = self.db.execute(query, filtros_base["params"])
        return [dict(row._mapping) for row in resultado]

    def guardar_resultados(self, registros: list[ContratoOutlier]) -> None:
        self.db.add_all(registros)
        self.db.flush()

    def obtener_ultimo_run_id(self) -> Optional[UUID]:
        resultado = self.db.execute(
            text("""
                SELECT run_id
                FROM contrato_outlier
                ORDER BY fecha_calculo DESC
                LIMIT 1
            """)
        ).fetchone()
        return resultado.run_id if resultado else None

    def obtener_outliers(
        self,
        run_id: UUID,
        solo_outliers: bool = False,
        grupo: Optional[str] = None,
        direccion: Optional[str] = None,
        score_minimo: Optional[float] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ContratoOutlier], int]:
        query = self.db.query(ContratoOutlier).filter(
            ContratoOutlier.run_id == run_id
        )

        if solo_outliers:
            query = query.filter(ContratoOutlier.es_outlier == True)
        if grupo:
            query = query.filter(ContratoOutlier.grupo == grupo)
        if direccion:
            query = query.filter(ContratoOutlier.direccion_outlier == direccion)
        if score_minimo is not None:
            query = query.filter(ContratoOutlier.score >= score_minimo)

        total = query.count()
        items = (
            query
            .order_by(ContratoOutlier.score.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def obtener_resumen_run(self, run_id: UUID) -> dict:
        resumen = self.db.execute(
            text("""
                SELECT
                    run_id,
                    campo_analizado,
                    COUNT(*)                                           AS total_analizados,
                    COUNT(*) FILTER (WHERE es_outlier = true)          AS total_outliers,
                    COUNT(*) FILTER (WHERE direccion_outlier = 'ALTO') AS total_alto,
                    COUNT(*) FILTER (WHERE direccion_outlier = 'BAJO') AS total_bajo,
                    COUNT(DISTINCT grupo)                              AS grupos_procesados,
                    MIN(fecha_calculo)                                 AS fecha_calculo
                FROM contrato_outlier
                WHERE run_id = :run_id
                GROUP BY run_id, campo_analizado
            """),
            {"run_id": str(run_id)}
        ).fetchone()

        por_grupo = self.db.execute(
            text("""
                SELECT
                    grupo,
                    MAX(q1)                                                  AS q1,
                    MAX(q3)                                                  AS q3,
                    MAX(iqr)                                                 AS iqr,
                    MAX(limite_inferior)                                     AS limite_inferior,
                    MAX(limite_superior)                                     AS limite_superior,
                    COUNT(*)                                                 AS total_contratos_analizados,
                    COUNT(*) FILTER (WHERE es_outlier = true)                AS total_outliers,
                    COUNT(*) FILTER (WHERE direccion_outlier = 'ALTO')       AS total_outliers_alto,
                    COUNT(*) FILTER (WHERE direccion_outlier = 'BAJO')       AS total_outliers_bajo
                FROM contrato_outlier
                WHERE run_id = :run_id
                GROUP BY grupo
                ORDER BY total_outliers DESC
            """),
            {"run_id": str(run_id)}
        ).fetchall()

        return {
            "resumen": dict(resumen._mapping) if resumen else {},
            "por_grupo": [dict(row._mapping) for row in por_grupo],
        }

    def _construir_filtros_base(
        self,
        campo: str,
        fecha_desde: Optional[date],
        fecha_hasta: Optional[date],
        modalidades: Optional[list[str]],
    ) -> dict:
        where_extra = ""
        params = {}

        if fecha_desde:
            where_extra += " AND fecha_publicacion_normalizada >= :fecha_desde"
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            where_extra += " AND fecha_publicacion_normalizada <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta
        if modalidades:
            where_extra += " AND modalidad_contratacion = ANY(:modalidades)"
            params["modalidades"] = modalidades

        return {"where_extra": where_extra, "params": params}

    # ------------------------------------------------------------------
    # LECTURA: duplicados en contratos_procesados
    # ------------------------------------------------------------------
    def obtener_pares_duplicados(
        self,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
    ) -> list[dict]:
        """
        Ejecuta el análisis de Window Functions para encontrar contratos del mismo
        proveedor, misma entidad, mismo tipo/modalidad con diferencia <= 30 días.
        """
        where_extra = ""
        params = {}
        if fecha_desde:
            where_extra += " AND fecha_publicacion_normalizada >= :fecha_desde"
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            where_extra += " AND fecha_publicacion_normalizada <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta

        query = text(f"""
            WITH Ventana AS (
                SELECT 
                    id, 
                    proveedor_normalizado, 
                    entidad_normalizada, 
                    tipo_contrato_normalizado, 
                    modalidad_contratacion, 
                    fecha_publicacion_normalizada,
                    LAG(id) OVER w AS prev_id,
                    LAG(fecha_publicacion_normalizada) OVER w AS prev_fecha
                FROM contratos_procesados
                WHERE proveedor_normalizado IS NOT NULL 
                  AND entidad_normalizada IS NOT NULL
                  AND fecha_publicacion_normalizada IS NOT NULL
                  AND es_incompleto = false
                  {where_extra}
                WINDOW w AS (
                    PARTITION BY proveedor_normalizado, entidad_normalizada, 
                                 COALESCE(tipo_contrato_normalizado, modalidad_contratacion)
                    ORDER BY fecha_publicacion_normalizada
                )
            )
            SELECT 
                id AS contrato_id, 
                prev_id AS contrato_relacionado_id, 
                proveedor_normalizado AS proveedor, 
                entidad_normalizada AS entidad, 
                tipo_contrato_normalizado AS tipo_contrato, 
                modalidad_contratacion,
                fecha_publicacion_normalizada AS fecha_contrato, 
                prev_fecha AS fecha_relacionada,
                (fecha_publicacion_normalizada - prev_fecha) AS diferencia_dias
            FROM Ventana
            WHERE prev_fecha IS NOT NULL 
              AND (fecha_publicacion_normalizada - prev_fecha) <= 30
        """)
        resultado = self.db.execute(query, params)
        return [dict(row._mapping) for row in resultado]

    # ------------------------------------------------------------------
    # ESCRITURA/LECTURA: contrato_duplicado_periodo
    # ------------------------------------------------------------------
    def guardar_duplicados(self, registros: list[ContratoDuplicadoPeriodo]) -> None:
        self.db.add_all(registros)
        self.db.flush()

    def obtener_ultimo_run_id_duplicados(self) -> Optional[UUID]:
        resultado = self.db.execute(
            text("""
                SELECT run_id
                FROM contrato_duplicado_periodo
                ORDER BY fecha_calculo DESC
                LIMIT 1
            """)
        ).fetchone()
        return resultado.run_id if resultado else None

    def obtener_duplicados_periodo(
        self,
        run_id: UUID,
        riesgo: Optional[str] = None,
        score_minimo: Optional[float] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ContratoDuplicadoPeriodo], int]:
        query = self.db.query(ContratoDuplicadoPeriodo).filter(
            ContratoDuplicadoPeriodo.run_id == run_id
        )

        if riesgo:
            query = query.filter(ContratoDuplicadoPeriodo.clasificacion_riesgo == riesgo)
        if score_minimo is not None:
            query = query.filter(ContratoDuplicadoPeriodo.duplicado_score >= score_minimo)

        total = query.count()
        items = (
            query
            .order_by(ContratoDuplicadoPeriodo.duplicado_score.desc(), ContratoDuplicadoPeriodo.diferencia_dias.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def obtener_resumen_duplicados_run(self, run_id: UUID) -> dict:
        resumen = self.db.execute(
            text("""
                SELECT
                    run_id,
                    COUNT(*) AS total_duplicados,
                    AVG(diferencia_dias) AS promedio_dias_diferencia,
                    AVG(duplicado_score) AS promedio_score,
                    MIN(fecha_calculo) AS fecha_calculo
                FROM contrato_duplicado_periodo
                WHERE run_id = :run_id
                GROUP BY run_id
            """),
            {"run_id": str(run_id)}
        ).fetchone()

        por_riesgo = self.db.execute(
            text("""
                SELECT
                    clasificacion_riesgo AS riesgo,
                    COUNT(*) AS total
                FROM contrato_duplicado_periodo
                WHERE run_id = :run_id
                GROUP BY clasificacion_riesgo
                ORDER BY total DESC
            """),
            {"run_id": str(run_id)}
        ).fetchall()

        return {
            "resumen": dict(resumen._mapping) if resumen else {},
            "por_riesgo": [dict(row._mapping) for row in por_riesgo],
        }

    # ------------------------------------------------------------------
    # LECTURA: cálculo de adjudicaciones directas desde contratos_procesados
    # ------------------------------------------------------------------

    def calcular_adjudicaciones_directas(
        self,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        minimo_directas: int = 3,
        dias_ventana: int = 90,
    ) -> list[dict]:
        """
        Ejecuta el análisis agregado de adjudicaciones directas por proveedor.
        Detecta proveedores con más de 'minimo_directas' adjudicaciones en un periodo.
        """
        where_extra = ""
        params: dict = {
            "minimo_directas": minimo_directas,
            "dias_ventana": dias_ventana
        }

        if fecha_desde:
            where_extra += " AND cp.fecha_publicacion_normalizada >= :fecha_desde"
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            where_extra += " AND cp.fecha_publicacion_normalizada <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta

        query = text(f"""
            WITH contratos_filtrados AS (
                SELECT
                    cp.id,
                    cp.proveedor_normalizado,
                    cp.nit_proveedor,
                    cp.entidad_normalizada,
                    cp.tipo_contrato_normalizado,
                    cp.modalidad_contratacion,
                    cp.fecha_publicacion_normalizada,
                    CASE 
                        WHEN (
                            LOWER(cp.modalidad_contratacion) LIKE '%directa%' 
                            OR LOWER(cp.modalidad_contratacion) LIKE '%contrataci_n_directa%'
                            OR LOWER(cp.modalidad_contratacion) LIKE '%contratacion_directa%'
                        )
                        THEN 1 ELSE 0 
                    END as es_directa
                FROM contratos_procesados cp
                WHERE cp.proveedor_normalizado IS NOT NULL
                  AND TRIM(cp.proveedor_normalizado) <> ''
                  AND UPPER(TRIM(cp.proveedor_normalizado)) NOT IN ('NO DEFINIDO', 'N/A', 'SIN INFORMACION', 'SIN INFORMACIÓN', 'SIN REGISTRO')
                  AND cp.fecha_publicacion_normalizada IS NOT NULL
                  {where_extra}
            ),

            resumen_proveedor AS (
                SELECT
                    proveedor_normalizado,
                    nit_proveedor,
                    COUNT(*)                                                   AS total_contratos,
                    SUM(es_directa)                                            AS contratos_directos,
                    MIN(fecha_publicacion_normalizada) FILTER (WHERE es_directa = 1) AS fecha_primera_directa,
                    MAX(fecha_publicacion_normalizada) FILTER (WHERE es_directa = 1) AS fecha_ultima_directa,
                    MAX(entidad_normalizada)                                   AS entidad,
                    MAX(tipo_contrato_normalizado)                             AS tipo_contrato,
                    MAX(modalidad_contratacion)                                AS modalidad_contratacion,
                    MAX(fecha_publicacion_normalizada)                         AS fecha_contrato,
                    MAX(id)                                                    AS contrato_id
                FROM contratos_filtrados
                GROUP BY proveedor_normalizado, nit_proveedor
            )

            SELECT
                proveedor_normalizado   AS proveedor,
                nit_proveedor,
                total_contratos,
                contratos_directos,
                ROUND(
                    (contratos_directos::numeric / NULLIF(total_contratos, 0)) * 100,
                    2
                )                       AS porcentaje_directos,
                entidad,
                tipo_contrato,
                modalidad_contratacion,
                fecha_contrato,
                contrato_id
            FROM resumen_proveedor
            WHERE contratos_directos >= :minimo_directas
              AND (fecha_ultima_directa - fecha_primera_directa) <= :dias_ventana
            ORDER BY contratos_directos DESC, porcentaje_directos DESC
        """)

        resultado = self.db.execute(query, params)
        return [dict(row._mapping) for row in resultado]

    # ------------------------------------------------------------------
    # ESCRITURA / LECTURA: proveedor_adjudicacion_directa
    # ------------------------------------------------------------------

    def guardar_adjudicaciones_directas(
        self, registros: list[ProveedorAdjudicacionDirecta]
    ) -> None:
        self.db.add_all(registros)
        self.db.flush()

    def obtener_ultimo_run_id_directas(self) -> Optional[UUID]:
        resultado = self.db.execute(
            text("""
                SELECT run_id
                FROM proveedor_adjudicacion_directa
                ORDER BY fecha_calculo DESC
                LIMIT 1
            """)
        ).fetchone()
        return resultado.run_id if resultado else None

    def obtener_proveedores_directas(
        self,
        run_id: UUID,
        riesgo: Optional[str] = None,
        score_minimo: Optional[float] = None,
        score_maximo: Optional[float] = None,
        porcentaje_minimo: Optional[float] = None,
        porcentaje_maximo: Optional[float] = None,
        solo_abuso_directas: bool = False,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ProveedorAdjudicacionDirecta], int]:
        query = self.db.query(ProveedorAdjudicacionDirecta).filter(
            ProveedorAdjudicacionDirecta.run_id == run_id
        )

        if riesgo:
            query = query.filter(ProveedorAdjudicacionDirecta.clasificacion_riesgo == riesgo)
        if score_minimo is not None:
            query = query.filter(ProveedorAdjudicacionDirecta.score_riesgo >= score_minimo)
        if score_maximo is not None:
            query = query.filter(ProveedorAdjudicacionDirecta.score_riesgo <= score_maximo)
        if porcentaje_minimo is not None:
            query = query.filter(ProveedorAdjudicacionDirecta.porcentaje_directos >= porcentaje_minimo)
        if porcentaje_maximo is not None:
            query = query.filter(ProveedorAdjudicacionDirecta.porcentaje_directos <= porcentaje_maximo)
        if solo_abuso_directas:
            query = query.filter(
                ProveedorAdjudicacionDirecta.clasificacion_riesgo.in_(["ALTO", "MEDIO"])
            )

        total = query.count()
        items = (
            query
            .order_by(
                ProveedorAdjudicacionDirecta.score_riesgo.desc(),
                ProveedorAdjudicacionDirecta.porcentaje_directos.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def obtener_resumen_directas(self, run_id: UUID) -> dict:
        resumen = self.db.execute(
            text("""
                SELECT
                    run_id,
                    COUNT(*)                       AS total_proveedores_detectados,
                    AVG(porcentaje_directos)        AS promedio_porcentaje_directos,
                    AVG(score_riesgo)               AS promedio_score,
                    MIN(fecha_calculo)              AS fecha_calculo
                FROM proveedor_adjudicacion_directa
                WHERE run_id = :run_id
                GROUP BY run_id
            """),
            {"run_id": str(run_id)},
        ).fetchone()

        por_riesgo = self.db.execute(
            text("""
                SELECT
                    clasificacion_riesgo AS riesgo,
                    COUNT(*)             AS total
                FROM proveedor_adjudicacion_directa
                WHERE run_id = :run_id
                GROUP BY clasificacion_riesgo
                ORDER BY total DESC
            """),
            {"run_id": str(run_id)},
        ).fetchall()

        return {
            "resumen": dict(resumen._mapping) if resumen else {},
            "por_riesgo": [dict(row._mapping) for row in por_riesgo],
        }

