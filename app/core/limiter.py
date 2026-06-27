import logging
from functools import wraps

from fastapi import Request, HTTPException

from app.core.settings import settings

logger = logging.getLogger(__name__)

# Инициализация Redis (оставляем как была)
redis_client = None
if settings.RATE_LIMIT_ENABLED:
    try:
        import redis

        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


def get_real_ip(request: Request) -> str:
    # 1. Приоритет Cloudflare
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip

    # 2. Обычный заголовок прокси (на случай Nginx без CF)
    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded:
        # Берем самый левый IP в списке
        return x_forwarded.split(",")[0].strip()

    # 3. Прямое подключение (локалка)
    return request.client.host


def rate_limit(requests: int, window_seconds: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            if not settings.RATE_LIMIT_ENABLED or redis_client is None:
                return await func(request, *args, **kwargs)

            # Используем вашу функцию для определения реального гостя
            ip = get_real_ip(request)
            key = f"rate_limit:{func.__module__}.{func.__name__}:{ip}"
            print("Rate limiting key:", key)
            try:
                current = redis_client.incr(key)
                if current == 1:
                    redis_client.expire(key, window_seconds)

                if current > requests:
                    # Можно добавить заголовок Retry-After для вежливости
                    raise HTTPException(
                        status_code=429,
                        detail=f"Too many requests. Limit: {requests} per {window_seconds}s"
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Rate limit error: {e}")
                return await func(request, *args, **kwargs)

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator