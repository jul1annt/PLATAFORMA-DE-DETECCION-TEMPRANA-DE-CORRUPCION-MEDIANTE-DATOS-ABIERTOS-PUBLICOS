from datetime import date
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from modules.analitica.model.contrato_outlier import ContratoOutlier
from modules.analitica.model.contrato_duplicado_periodo import ContratoDuplicadoPeriodo
from modules.analitica.model.proveedor_adjudicacion_directa import ProveedorAdjudicacionDirecta
from modules.analitica.model.peso_anomalia import PesoAnomalia
from modules.analitica.model.riesgo_proveedor import RiesgoProveedor



class AnaliticaRepository:

    def __init__(self, db: Session):
        self.db = db

    def obtener_estadisticas_por_grupo(
        self,
        campo: str,
        fecha_campo: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        modalidades: Optional[list[str]] = None,
        modalidad: Optional[str] = None,
    ) -> list[dict]:
        # Validar rigurosamente contra allowlist antes de interpolar en query SQL
        CAMPOS_NUMERICOS_VALIDOS = {"valor_total_normalizado", "precio_base_normalizado", "nivel_confianza", "cantidad_campos_faltantes"}
        if campo not in CAMPOS_NUMERICOS_VALIDOS:
            raise ValueError(f"Campo numérico no válido: {campo}")

        filtros_base = self._construir_filtros_base(
            campo=campo,
            fecha_campo=fecha_campo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            modalidades=modalidades,
            modalidad=modalidad,
        )

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
        fecha_campo: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        modalidades: Optional[list[str]] = None,
        modalidad: Optional[str] = None,
    ) -> list[dict]:
        # Validar rigurosamente contra allowlist antes de interpolar en query SQL
        CAMPOS_NUMERICOS_VALIDOS = {"valor_total_normalizado", "precio_base_normalizado", "nivel_confianza", "cantidad_campos_faltantes"}
        if campo not in CAMPOS_NUMERICOS_VALIDOS:
            raise ValueError(f"Campo numérico no válido: {campo}")

        filtros_base = self._construir_filtros_base(
            campo=campo,
            fecha_campo=fecha_campo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            modalidades=modalidades,
            modalidad=modalidad,
        )

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
        fecha_campo: Optional[str] = None,
        fecha_desde: Optional[date] = None,
        fecha_hasta: Optional[date] = None,
        modalidades: Optional[list[str]] = None,
        modalidad: Optional[str] = None,
    ) -> dict:
        where_extra = ""
        params = {}

        # Determinar qué columna de fecha usar. Por defecto es fecha_publicacion_normalizada.
        # Validar rigurosamente contra allowlist antes de cualquier interpolación.
        CAMPOS_FECHA_VALIDOS = {"fecha_publicacion_normalizada", "fecha_adjudicacion_normalizada"}
        col_fecha = "fecha_publicacion_normalizada"
        if fecha_campo:
            if fecha_campo not in CAMPOS_FECHA_VALIDOS:
                raise ValueError(f"Campo de fecha no válido: {fecha_campo}")
            col_fecha = fecha_campo

        if fecha_desde:
            where_extra += f" AND {col_fecha} >= :fecha_desde"
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            where_extra += f" AND {col_fecha} <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta
        if modalidades:
            where_extra += " AND modalidad_contratacion = ANY(:modalidades)"
            params["modalidades"] = modalidades

        # Filtro de modalidad única (nuevo requisito de selección única)
        if modalidad:
            where_extra += " AND modalidad_contratacion = :modalidad"
            params["modalidad"] = modalidad

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

    # ==================================================================
    # RIESGO COMBINADO Y PESOS
    # ==================================================================

    def inicializar_pesos(self) -> None:
        """Inicializa los pesos por defecto si no existen."""
        pesos_default = {
            "OUTLIER": 1.0,
            "DUPLICADO_CORTO": 1.5,
            "ABUSO_DIRECTO": 2.0
        }
        for tipo, peso in pesos_default.items():
            existe = self.db.query(PesoAnomalia).filter_by(tipo_anomalia=tipo).first()
            if not existe:
                nuevo = PesoAnomalia(tipo_anomalia=tipo, peso=peso)
                self.db.add(nuevo)
        self.db.commit()

    def obtener_pesos(self) -> list[PesoAnomalia]:
        self.inicializar_pesos()
        return self.db.query(PesoAnomalia).all()

    def actualizar_peso(self, tipo_anomalia: str, peso: float) -> Optional[PesoAnomalia]:
        obj = self.db.query(PesoAnomalia).filter_by(tipo_anomalia=tipo_anomalia).first()
        if obj:
            obj.peso = peso
            self.db.commit()
            self.db.refresh(obj)
            return obj
        return None

    def obtener_scores_combinados_por_proveedor(self) -> list[dict]:
        """
        Cruza los datos de las tres tablas de analítica usando el ÚLTIMO run_id de cada una,
        para obtener el score máximo de cada anomalía por proveedor.
        """
        run_outlier = self.obtener_ultimo_run_id()
        run_duplicado = self.obtener_ultimo_run_id_duplicados()
        run_directa = self.obtener_ultimo_run_id_directas()

        # Usar gen_random_uuid o 0 si no hay run_id para que el query no falle
        ro = f"'{run_outlier}'" if run_outlier else 'NULL'
        rd = f"'{run_duplicado}'" if run_duplicado else 'NULL'
        ra = f"'{run_directa}'" if run_directa else 'NULL'

        query = text(f"""
            WITH outliers AS (
                SELECT 
                    cp.proveedor_normalizado AS proveedor,
                    cp.nit_proveedor,
                    MAX(co.score) AS max_score_outlier
                FROM contrato_outlier co
                JOIN contratos_procesados cp ON co.contrato_id = cp.id
                WHERE co.run_id = {ro} AND cp.proveedor_normalizado IS NOT NULL
                GROUP BY cp.proveedor_normalizado, cp.nit_proveedor
            ),
            duplicados AS (
                SELECT 
                    proveedor,
                    NULL AS nit_proveedor, -- En duplicados a veces no tenemos el nit guardado, usamos proveedor
                    MAX(duplicado_score) AS max_score_duplicado
                FROM contrato_duplicado_periodo
                WHERE run_id = {rd} AND proveedor IS NOT NULL
                GROUP BY proveedor
            ),
            directas AS (
                SELECT 
                    proveedor,
                    nit_proveedor,
                    MAX(score_riesgo) AS score_directo
                FROM proveedor_adjudicacion_directa
                WHERE run_id = {ra} AND proveedor IS NOT NULL
                GROUP BY proveedor, nit_proveedor
            ),
            proveedores AS (
                SELECT proveedor, nit_proveedor FROM outliers
                UNION
                SELECT proveedor, nit_proveedor FROM duplicados WHERE nit_proveedor IS NOT NULL
                UNION
                SELECT proveedor, NULL FROM duplicados WHERE nit_proveedor IS NULL
                UNION
                SELECT proveedor, nit_proveedor FROM directas
            )
            SELECT 
                p.proveedor,
                MAX(p.nit_proveedor) AS nit_proveedor,
                COALESCE(MAX(o.max_score_outlier), 0) AS max_score_outlier,
                COALESCE(MAX(d.max_score_duplicado), 0) AS max_score_duplicado,
                COALESCE(MAX(a.score_directo), 0) AS score_directo
            FROM proveedores p
            LEFT JOIN outliers o ON p.proveedor = o.proveedor
            LEFT JOIN duplicados d ON p.proveedor = d.proveedor
            LEFT JOIN directas a ON p.proveedor = a.proveedor
            WHERE p.proveedor IS NOT NULL AND p.proveedor <> ''
            GROUP BY p.proveedor
        """)

        resultado = self.db.execute(query)
        return [dict(row._mapping) for row in resultado]

    def guardar_riesgo_proveedores(self, registros: list[RiesgoProveedor]) -> None:
        self.db.add_all(registros)
        self.db.flush()

    def obtener_ultimo_run_id_riesgo(self) -> Optional[UUID]:
        resultado = self.db.execute(
            text("""
                SELECT run_id
                FROM riesgo_proveedor
                ORDER BY fecha_calculo DESC
                LIMIT 1
            """)
        ).fetchone()
        return resultado.run_id if resultado else None

    def obtener_riesgos(
        self,
        run_id: UUID,
        proveedor: Optional[str] = None,
        riesgo: Optional[str] = None,
        score_minimo: Optional[float] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[RiesgoProveedor], int]:
        query = self.db.query(RiesgoProveedor).filter(
            RiesgoProveedor.run_id == run_id
        )

        if proveedor:
            query = query.filter(RiesgoProveedor.proveedor.ilike(f"%{proveedor}%"))
        if riesgo:
            query = query.filter(RiesgoProveedor.clasificacion_riesgo == riesgo)
        if score_minimo is not None:
            query = query.filter(RiesgoProveedor.score_final >= score_minimo)

        total = query.count()
        items = (
            query
            .order_by(RiesgoProveedor.score_final.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def obtener_resumen_riesgo(self, run_id: UUID) -> dict:
        resumen = self.db.execute(
            text("""
                SELECT
                    run_id,
                    COUNT(*) AS total_proveedores_evaluados,
                    AVG(score_final) AS promedio_score_final,
                    MIN(fecha_calculo) AS fecha_calculo
                FROM riesgo_proveedor
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
                FROM riesgo_proveedor
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
