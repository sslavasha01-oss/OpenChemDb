from app.core.settings import settings
from app.schemas.user import UserOut
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, allow_admin
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Возвращает информацию о текущем залогиненном пользователе.
    Доступен только если в заголовке передан валидный JWT.
    """
    # Динамически вычисляем максимальный размер по тарифу пользователя
    if not settings.LOCAL_MODE:
        user_tariff = getattr(current_user, "tariff_plan")
        max_size = settings.TARIFF_LIMITS.get(user_tariff)

        current_user.max_allowed_size = max_size
    else:
        current_user.max_allowed_size = 0

    # Добавляем свойство в объект SQLAlchemy, чтобы Pydantic смог его подтянуть
    return current_user

@router.get("/test-auth")
async def test_auth(current_user: User = Depends(get_current_user)):
    """
    Простой эндпоинт для проверки связи.
    """
    return {
        "status": "ok",
        "message": f"Hello, {current_user.username}! Your token is valid.",
        "your_role": current_user.role
    }

@router.get("/stats")
async def get_admin_stats(admin_user: User = Depends(allow_admin)):
    """
    Этот эндпоинт вернет данные только если у пользователя role == 'ADMIN'.
    Если зайдет обычный USER, он получит 403 Forbidden.
    """
    return {
        "status": "access_granted",
        "admin_username": admin_user.username,
        "server_info": "Database schema: chemistry_archive, chemistry_user is active",
        "message": "Welcome to the secret laboratory, Boss!"
    }