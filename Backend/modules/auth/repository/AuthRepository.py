from sqlalchemy.orm import Session
from modules.auth.model.Admin import Admin

class AuthRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> Admin | None:
        return self.db.query(Admin).filter(
            Admin.username == username,
            Admin.is_active == True
        ).first()

    def get_by_id(self, admin_id: int) -> Admin | None:
        return self.db.query(Admin).filter(Admin.id == admin_id).first()

    def create(self, admin: Admin) -> Admin:
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin

    def exists_any_admin(self) -> bool:
        return self.db.query(Admin).count() > 0