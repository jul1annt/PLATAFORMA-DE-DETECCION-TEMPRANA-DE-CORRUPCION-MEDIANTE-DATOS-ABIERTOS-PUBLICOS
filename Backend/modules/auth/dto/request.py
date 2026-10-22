import unicodedata

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_password_text(password: str, *, minimum: int) -> str:
    if not password.strip():
        raise ValueError("La contraseña no puede estar vacía ni contener solo espacios")
    if any(unicodedata.category(character) == "Cc" for character in password):
        raise ValueError("La contraseña no puede contener caracteres de control")
    if not minimum <= len(password) <= 128:
        raise ValueError(f"La contraseña debe tener entre {minimum} y 128 caracteres")
    return password

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_login_password(cls, value: str) -> str:
        return validate_password_text(value, minimum=8)

class CreateAdminRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_new_admin_password(cls, value: str) -> str:
        return validate_password_text(value, minimum=12)
