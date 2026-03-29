from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import get_users_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, Token
from app.core.security import get_password_hash
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-local", response_model=UserOut)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_users_db)):
    # 1. Проверяем, нет ли уже такого юзера
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    # 2. Хешируем пароль и создаем объект
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role="USER"  # По умолчанию все регистрируются как обычные юзеры
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_users_db)
):
    # 1. Ищем юзера по username
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    # 2. Проверяем существование и пароль
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Генерируем токен (он будет вечным, если AUTHORIZATION_NEVER_EXPIRES=true)
    access_token = create_access_token(data={"id" : user.id, "sub": user.username, "role": user.role})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role
    }