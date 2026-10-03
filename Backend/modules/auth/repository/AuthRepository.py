import hashlib
from datetime import datetime

from sqlalchemy import delete, func, text
from sqlalchemy.orm import Session
from modules.auth.model.Admin import Admin
from modules.auth.model.AdminSession import AdminSession
from modules.auth.model.LoginAttempt import LoginAttempt


class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str, active_only: bool = True) -> Admin | None:
        query = self.db.query(Admin).filter(func.lower(Admin.username) == username.lower())
        if active_only:
            query = query.filter(Admin.is_active.is_(True))
        return query.first()

    def get_by_id(self, admin_id: int, active_only: bool = True) -> Admin | None:
        query = self.db.query(Admin).filter(Admin.id == admin_id)
        if active_only:
            query = query.filter(Admin.is_active.is_(True))
        return query.first()

    def get_by_email(self, email: str) -> Admin | None:
        return self.db.query(Admin).filter(func.lower(Admin.email) == email.lower()).first()

    def create(self, admin: Admin) -> Admin:
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def exists_any_admin(self) -> bool:
        return self.db.query(Admin).count() > 0

    def create_session(self, session: AdminSession) -> None:
        self.db.add(session)
        self.db.commit()

    def get_active_session(self, jti: str, now: datetime) -> AdminSession | None:
        return self.db.query(AdminSession).filter(
            AdminSession.jti == jti,
            AdminSession.revoked.is_(False),
            AdminSession.expires_at > now,
        ).first()

    def revoke_session(self, jti: str, now: datetime) -> bool:
        session = self.db.query(AdminSession).filter(AdminSession.jti == jti).first()
        if not session:
            return False
        session.revoked = True
        session.revoked_at = now
        self.db.commit()
        return True

    def revoke_all_sessions(self, admin_id: int, now: datetime) -> None:
        self.db.query(AdminSession).filter(
            AdminSession.admin_id == admin_id,
            AdminSession.revoked.is_(False),
        ).update({"revoked": True, "revoked_at": now}, synchronize_session=False)
        self.db.commit()

    def count_recent_failures(self, login_key: str, since: datetime) -> int:
        return self.db.query(LoginAttempt).filter(
            LoginAttempt.login_key == login_key,
            LoginAttempt.attempted_at >= since,
        ).count()

    def lock_login_attempts(self, login_key: str) -> None:
        """Serialize rate-limit decisions across API processes for one login key."""
        lock_key = int.from_bytes(
            hashlib.sha256(login_key.encode("ascii")).digest()[:8],
            byteorder="big",
            signed=True,
        )
        self.db.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )

    def record_failure(self, login_key: str) -> None:
        self.db.add(LoginAttempt(login_key=login_key))
        self.db.commit()

    def clear_failures(self, login_key: str) -> None:
        self.db.execute(delete(LoginAttempt).where(LoginAttempt.login_key == login_key))
        self.db.commit()
