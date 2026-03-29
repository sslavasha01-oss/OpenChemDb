from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import settings

# Двигатель для базы пользователей (обычно нагрузка ниже)
users_engine = create_async_engine(
    settings.USERS_DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

# Двигатель для базы пользователей
users_session_factory = async_sessionmaker(users_engine, expire_on_commit=False)

# Двигатель для базы архива (3 млн реакций — здесь важна стабильность)
archive_engine = create_async_engine(
    settings.ARCHIVE_DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=1800,
    pool_pre_ping=True
)

archive_session_factory = async_sessionmaker(archive_engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_users_db():
    async with users_session_factory() as session:
        yield session

# Зависимость для сессии архива (search, big data)
async def get_archive_db():
    async with archive_session_factory() as session:
        yield session


import time
import logging
from sqlalchemy import event

# Настраиваем логирование (можно в отдельный файл или в консоль)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openchem_db")

# Порог "медленного" запроса в секундах для архива
SLOW_QUERY_THRESHOLD_ARCHIVE_DB = 1.0

# Порог "медленного" запроса в секундах для юзер дб
SLOW_QUERY_THRESHOLD_USER_DB = 1.0


@event.listens_for(archive_engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Сохраняем время старта в контексте запроса
    context._query_start_time = time.time()


@event.listens_for(archive_engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Считаем разницу
    total_time = time.time() - context._query_start_time

    # Если запрос медленный — пишем в лог
    if total_time > SLOW_QUERY_THRESHOLD_ARCHIVE_DB:
        logger.warning(
            f"\n--- SLOW QUERY DETECTED ARCHIVE_DB({total_time:.2f}s) ---\n"
            f"SQL: {statement}\n"
            f"Params: {parameters}\n"
            f"-------------------------------------------"
        )

@event.listens_for(users_engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Сохраняем время старта в контексте запроса
    context._query_start_time = time.time()


@event.listens_for(users_engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Считаем разницу
    total_time = time.time() - context._query_start_time

    # Если запрос медленный — пишем в лог
    if total_time > SLOW_QUERY_THRESHOLD_USER_DB:
        logger.warning(
            f"\n--- SLOW QUERY DETECTED USER_DB ({total_time:.2f}s) ---\n"
            f"SQL: {statement}\n"
            f"Params: {parameters}\n"
            f"-------------------------------------------"
        )