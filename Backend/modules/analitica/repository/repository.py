from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo


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
