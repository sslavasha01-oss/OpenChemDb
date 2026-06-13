from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_users_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, Token
from app.core.security import get_password_hash
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, create_access_token
from app.core.settings import settings


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_users_db)
):
    # 1. Ищем юзера по username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Проверяем существование и пароль (пароль игнорируем, если включен NO_PASSWORD_LOGIN)
    is_password_valid = True if settings.NO_PASSWORD_LOGIN else verify_password(form_data.password,
                                                                                user.hashed_password)

    if not user or not is_password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 3. Генерируем токен (он будет вечным, если AUTHORIZATION_NEVER_EXPIRES=true)
    access_token = create_access_token(data={"id" : user.id, "sub": user.username, "role": user.role})
    return {
        "user_id": user.id,
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }