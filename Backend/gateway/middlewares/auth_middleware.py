from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.database import get_db
from modules.auth.service.AuthService import AuthService
from modules.auth.dto.response import AdminResponse

bearer_scheme = HTTPBearer()

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> AdminResponse:
    service = AuthService(db)
    return service.get_current_admin(credentials.credentials)