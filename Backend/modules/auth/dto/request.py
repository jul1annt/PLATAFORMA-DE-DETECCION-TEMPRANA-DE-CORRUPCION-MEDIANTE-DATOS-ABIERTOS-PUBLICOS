from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateAdminRequest(BaseModel):
    username: str
    email: EmailStr
    password: str