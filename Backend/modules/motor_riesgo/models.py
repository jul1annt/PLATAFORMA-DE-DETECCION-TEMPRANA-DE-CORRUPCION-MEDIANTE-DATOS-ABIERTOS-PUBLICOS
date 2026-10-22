"""Additive persistence: the historical source and provider scores are untouched."""
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Boolean, ForeignKey, Index, Text, CheckConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from shared.base_model import Base


class JudicialCase(Base):
    __tablename__ = 'riesgo_casos'
    case_id = Column(String(100), primary_key=True)
    record = Column(JSONB, nullable=False)
    record_sha256 = Column(String(64), nullable=False)
    eligible = Column(Boolean, nullable=False, default=False)
    exclusions = Column(JSONB, nullable=False, default=list)
    registered_by = Column(Integer, ForeignKey('admins.id'), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskModel(Base):
    __tablename__ = 'riesgo_modelos'
    id = Column(UUID(as_uuid=True), primary_key=True)
    stage = Column(String(20), nullable=False)
    version = Column(String(100), nullable=False, unique=True)
    artifact = Column(JSONB, nullable=False)
    report = Column(JSONB, nullable=False)
    validated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskFeatureEvidence(Base):
    __tablename__ = 'riesgo_evidencias_variables'
    evidence_id = Column(String(100), primary_key=True)
    record = Column(JSONB, nullable=False)
    record_sha256 = Column(String(64), nullable=False)
    registered_by = Column(Integer, ForeignKey('admins.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    raw_secop_id = Column(BigInteger, ForeignKey('raw_secop.id'))
    stage = Column(String(20))
    prediction_at = Column(DateTime(timezone=True))
    __table_args__ = (
        Index('ix_riesgo_evidencia_operacion_etapa','raw_secop_id','stage','created_at'),
        CheckConstraint("(raw_secop_id IS NULL AND stage IS NULL AND prediction_at IS NULL) OR "
                        "(raw_secop_id IS NOT NULL AND raw_secop_id>0 AND stage IS NOT NULL AND stage IN ('CONVOCATORIA','ADJUDICACION') AND prediction_at IS NOT NULL)",
                        name='ck_riesgo_evidencia_etapa'),)


class RiskCut(Base):
    __tablename__ = 'riesgo_cortes'
    id = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String(30), nullable=False, default='PREPARANDO')
    context = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))


class RiskResult(Base):
    __tablename__ = 'riesgo_resultados'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    cut_id = Column(UUID(as_uuid=True), ForeignKey('riesgo_cortes.id'), nullable=False)
    raw_secop_id = Column(BigInteger, ForeignKey('raw_secop.id'), nullable=False)
    stage = Column(String(20), nullable=False)
    result = Column(JSONB, nullable=False)
    __table_args__ = (Index('uq_riesgo_resultado_operacion', 'cut_id', 'raw_secop_id', 'stage', unique=True),)


class RiskPublication(Base):
    __tablename__ = 'riesgo_publicacion'
    id = Column(Integer, primary_key=True)
    cut_id = Column(UUID(as_uuid=True), ForeignKey('riesgo_cortes.id'), nullable=True)
    model_ids = Column(JSONB, nullable=False, default=dict)
    daily_enabled = Column(Boolean, nullable=False, default=False)
    last_attempt_day = Column(String(10), nullable=True)
    last_success_day = Column(String(10), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskAudit(Base):
    __tablename__ = 'riesgo_auditoria'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    action = Column(String(60), nullable=False)
    actor = Column(String(100), nullable=False)
    detail = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RiskDataVersion(Base):
    __tablename__ = 'riesgo_versiones_datos'
    table_name = Column(String(60), primary_key=True)
    epoch = Column(UUID(as_uuid=True), nullable=False)
    revision = Column(BigInteger, nullable=False)
    row_count = Column(BigInteger, nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    __table_args__ = (CheckConstraint('row_count>=0 AND revision>=0', name='ck_riesgo_versiones_nonnegative'),)


class CitizenSnapshot(Base):
    __tablename__ = 'riesgo_cortes_ciudadanos'
    id = Column(UUID(as_uuid=True), primary_key=True)
    revision = Column(BigInteger, nullable=False)
    risk_cut_id = Column(UUID(as_uuid=True), ForeignKey('riesgo_cortes.id'))
    data_cut_at = Column(String(50), nullable=False)
    aggregates = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CitizenPublication(Base):
    __tablename__ = 'riesgo_publicacion_ciudadana'
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(UUID(as_uuid=True), ForeignKey('riesgo_cortes_ciudadanos.id'), nullable=False)
