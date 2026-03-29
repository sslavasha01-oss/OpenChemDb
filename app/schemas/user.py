from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Что юзер присылает при регистрации
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

# Что мы возвращаем клиенту (без пароля!)
class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True # Позволяет Pydantic работать с объектами SQLAlchemy

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str # Добавим роль в ответ, чтобы фронтенд сразу знал, что рисовать

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordUpdate(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)