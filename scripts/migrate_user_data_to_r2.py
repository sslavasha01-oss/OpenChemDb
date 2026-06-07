import os
import mimetypes
from pathlib import Path
import boto3
from botocore.config import Config

from app.core.settings import settings

# Загрузка переменных окружения

# --- Ваши настройки ---
# (Предполагается, что project_root определяется в вашем проекте, здесь для примера берем текущую директорию)
project_root = os.path.dirname(os.path.abspath(__file__))

USER_DATA_STORAGE_PATH: str = settings.USER_DATA_STORAGE_PATH
R2_USER_DATA_STORAGE_PATH: str = settings.R2_USER_DATA_STORAGE_PATH

# Инициализация клиента Boto3 для Cloudflare R2 token value cfat_3CLj1zu8IV9CXJ5TQDsPFsuz33RRdeK31iBXC2E2cc99cf15
account_id = settings.R2_ACCOUNT_ID
access_key = settings.R2_ACCESS_KEY
secret_key = settings.R2_SECRET_KEY
bucket_name = settings.R2_BUCKET_NAME

s3_client = boto3.client(
    service_name="s3",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4"),
)


def migrate_files():
    local_path = Path(USER_DATA_STORAGE_PATH)

    if not local_path.exists():
        print(f" Локальная директория {local_path} не найдена. Нечего мигрировать.")
        return

    print(f" Начинается миграция из: {local_path}")
    print(f" Целевой путь в R2: {R2_USER_DATA_STORAGE_PATH}/\n")

    success_count = 0
    fail_count = 0

    # Рекурсивный обход всех файлов
    for file_path in local_path.rglob("*"):
        if file_path.is_file():
            # Вычисляем относительный путь файла для сохранения структуры папок
            relative_path = file_path.relative_to(local_path)

            # Формируем ключ (путь) для R2
            # Переводим в posix-формат (с косой чертой '/'), чтобы пути корректно работали на Windows
            r2_key = f"{R2_USER_DATA_STORAGE_PATH}/{relative_path.as_posix()}"

            # Автоопределение Content-Type (важно для корректного открытия файлов/картинок в браузере)
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

            print(f"Загрузка: {relative_path} -> {r2_key} ({content_type})...")

            try:
                s3_client.upload_file(
                    Filename=str(file_path),
                    Bucket=bucket_name,
                    Key=r2_key,
                    ExtraArgs={"ContentType": content_type}
                )
                success_count += 1
            except Exception as e:
                print(f" Ошибка при загрузке {relative_path}: {e}")
                fail_count += 1

    print("\n" + "=" * 40)
    print(" Миграция завершена!")
    print(f" Успешно загружено: {success_count} файлов.")
    if fail_count > 0:
        print(f" Ошибок: {fail_count}")
    print("=" * 40)


if __name__ == "__main__":
    migrate_files()