from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from shared.base_model import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True)
    login_key = Column(String(64), nullable=False, index=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
