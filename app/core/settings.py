from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pydantic import EmailStr

# Находим путь к папке, где лежит этот файл (app/core)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Поднимаемся на два уровня выше до корня (Platform)
project_root = os.path.dirname(os.path.dirname(current_dir))
# Склеиваем путь к .env
env_path = os.path.join(project_root, ".env")


class Settings(BaseSettings):
    # --- Основные настройки ---
    PROJECT_NAME: str = "OpenChemDB"
    # Секретный ключ для JWT
    SECRET_KEY: str = "super-secret-key-change-me-in-production"
    ALGORITHM: str = "HS256"

    ENV: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # Включать ли базу журнальных методик (spresi)
    JOURNAL_BASE: bool = True

    # Включать ли базу книжных методик
    BOOK_BASE: bool = True

    # Включать ли публичную базу журналов
    PUBLIC_JOURNAL: bool = True

    # Токены на 100 лет (для локального использования)
    AUTHORIZATION_NEVER_EXPIRES: bool = True

    # Вход в один клик без пароля (гостевой режим)
    NO_PASSWORD_LOGIN: bool = False

    # --- Настройки БД ---
    USERS_DATABASE_URL: str
    ARCHIVE_DATABASE_URL: str

    TIMEZONE: str = "UTC"

    SEARCH_LIMIT: int = 200

    # Указываем путь именно к SOP
    SOP_STORAGE_PATH: str = os.path.join(project_root, "data", "SOP")

    MAIL_TOKEN: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str = "OpenChemDB Admin"

    # URL бекенда, нужен для редиректов
    BACKEND_URL: str = "http://localhost:8000"

    # Эти настройки лучше вынести в settings/env
    # Для N100: POOL_SIZE=5, MAX_OVERFLOW=10
    # Для 18-ядерника: POOL_SIZE=3, MAX_OVERFLOW=5 (так как воркеров будет много)
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    RATE_LIMIT_ENABLED: bool = False

    # Магия Pydantic:
    # 1. Сначала смотрим реальные переменные окружения (ОС)
    # 2. Если их нет, пробуем прочитать .env (полезно для локальной разработки без Docker)
    model_config = SettingsConfigDict(
        env_file=env_path,
        env_file_encoding='utf-8',
        extra='ignore'  # Игнорировать лишние переменные в .env
    )


# Создаем экземпляр настроек для импорта в другие файлы
settings = Settings()

if settings.ENV == "prod":
    settings.RATE_LIMIT_ENABLED = True