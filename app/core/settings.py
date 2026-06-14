from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pydantic import EmailStr
from typing import ClassVar, Dict

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

    # Токены на 100 лет (для локального использования)
    AUTHORIZATION_NEVER_EXPIRES: bool = True

    # --- Настройки БД ---
    USERS_DATABASE_URL: str
    ARCHIVE_DATABASE_URL: str

    SEARCH_LIMIT: int = 200
    STATEMENT_TIMEOUT: int = 5000

    # Указываем путь именно к SOP
    SOP_STORAGE_PATH: str = os.path.join(project_root, "data", "SOP")
    USER_DATA_STORAGE_PATH: str = os.path.join(project_root, "data", "user_files")

    R2_USER_DATA_STORAGE_PATH: str = "user_files"
    R2_ACCOUNT_ID: str
    R2_ACCESS_KEY: str
    R2_SECRET_KEY: str
    R2_BUCKET_NAME: str

    MAIL_TOKEN: str
    MAIL_FROM: EmailStr
    MAIL_FROM_NAME: str = "OpenChemDB Admin"

    # URL бекенда, нужен для редиректов
    BACKEND_URL: str = "http://localhost:8000"

    # Для 18-ядерника: POOL_SIZE=3, MAX_OVERFLOW=5 (так как воркеров будет много)
    DB_POOL_SIZE: int = 3
    DB_MAX_OVERFLOW: int = 5

    RATE_LIMIT_ENABLED: bool = False

    # Максимальный размер файла в байтах (25 MB = 25 * 1024 * 1024)
    MAX_FILE_SIZE: int = 25 * 1024 * 1024

    LOCAL_MODE: bool
    NO_PASSWORD_LOGIN: bool

    TARIFF_LIMITS: ClassVar[Dict[str, int]] = {
        "FREE": 1 * 1024 * 1024 * 1024,
        "PAID_1": 50 * 1024 * 1024 * 1024
    }

    BMAC_SIGNING_SECRET: str
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