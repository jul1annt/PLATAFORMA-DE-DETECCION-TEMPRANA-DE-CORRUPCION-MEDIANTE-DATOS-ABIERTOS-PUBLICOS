"""Exact transactional aggregate maintained by PostgreSQL triggers."""
from sqlalchemy import BigInteger, CheckConstraint, Column, Numeric, SmallInteger, text
from shared.base_model import Base


class ContratoMetricasCalidad(Base):
    __tablename__ = 'contratos_metricas_calidad'

    id = Column(SmallInteger, primary_key=True)
    total = Column(BigInteger, nullable=False, server_default=text('0'))
    incompletos = Column(BigInteger, nullable=False, server_default=text('0'))
    sospechosos = Column(BigInteger, nullable=False, server_default=text('0'))
    alto_riesgo = Column(BigInteger, nullable=False, server_default=text('0'))
    con_confianza = Column(BigInteger, nullable=False, server_default=text('0'))
    suma_confianza = Column(Numeric(38, 0), nullable=False, server_default=text('0'))
    riesgo_desde_revision = Column(BigInteger, nullable=False, server_default=text('0'))

    __table_args__ = (
        CheckConstraint('id = 1', name='ck_cmc_singleton'),
        CheckConstraint('total >= 0 AND incompletos BETWEEN 0 AND total AND sospechosos BETWEEN 0 AND total AND alto_riesgo BETWEEN 0 AND total AND con_confianza BETWEEN 0 AND total', name='ck_cmc_counts'),
        {'schema': 'public'},
    )
