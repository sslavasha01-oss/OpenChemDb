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
    billing_email: Optional[EmailStr] = None
    role: str
    is_active: bool
    tariff_plan: str
    max_allowed_size: int  # Вычисляемое поле для фронта
    attachments_total_size: int

    class Config:
        from_attributes = True # Позволяет Pydantic работать с объектами SQLAlchemy

class Token(BaseModel):
    user_id: int
    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    role: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordUpdate(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)