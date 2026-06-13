from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.settings import settings
from app.core.db import get_users_db
from app.models.export import UserExport, ProcessStatus
from app.models.user import User
from fastapi import Depends, HTTPException, status, Request
from typing import List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
        db: AsyncSession = Depends(get_users_db),
        token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled/inactive"
        )

    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have enough permissions (Admin only)"
            )
        return user


allow_admin = RoleChecker(["ADMIN"])


async def check_database_lock(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_users_db)
) -> None:
    """
    Зависимость для проверки блокировки БД пользователя.
    Выбрасывает 423 Locked, если идет процесс импорта или экспорта.
    """
    # Запрашиваем записи процессов для текущего пользователя
    stmt = select(UserExport).where(UserExport.user_id == current_user.id)
    res = await db.execute(stmt)
    active_processes = res.scalars().all()

    for process in active_processes:
        if process.status in (ProcessStatus.PROCESSING_IMPORT, ProcessStatus.PROCESSING_EXPORT):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Database locked by background process: {process.status}"
            )
