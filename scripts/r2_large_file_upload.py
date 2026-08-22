import os
import sys
import time
import boto3
from botocore.config import Config
from boto3.s3.transfer import TransferConfig
from app.core.settings import settings

# ==========================================
# КОНФИГУРАЦИЯ CLOUDFLARE R2 / S3
# ==========================================
ACCOUNT_ID = settings.R2_ACCOUNT_ID
ACCESS_KEY_ID = settings.R2_PUBLIC_BUCKET_ACCESS_KEY
SECRET_ACCESS_KEY = settings.R2_PUBLIC_BUCKET_SECRET_KEY
BUCKET_NAME = settings.R2_PUBLIC_BUCKET_BUCKET_NAME

# Для Cloudflare R2 endpoint имеет формат: https://<ACCOUNT_ID>.r2.cloudflarestorage.com
ENDPOINT_URL = f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"

FILE_PATH = "data.7z"
OBJECT_NAME = "database-dump/data.7z"  # Имя объекта в R2 бакете


# ==========================================
# ПРОГРЕСС-БАР С ОТОБРАЖЕНИЕМ СКОРОСТИ
# ==========================================
class ProgressPercentage:
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._start_time = time.time()

    def __call__(self, bytes_amount):
        self._seen_so_far += bytes_amount
        percentage = (self._seen_so_far / self._size) * 100
        elapsed = time.time() - self._start_time
        speed_mbps = (self._seen_so_far / (1024 * 1024)) / elapsed if elapsed > 0 else 0

        uploaded_gb = self._seen_so_far / (1024 ** 3)
        total_gb = self._size / (1024 ** 3)

        sys.stdout.write(
            f"\r[Прогресс]: {uploaded_gb:.2f} / {total_gb:.2f} GB "
            f"({percentage:.2f}%) | Скорость: {speed_mbps:.2f} MB/s"
        )
        sys.stdout.flush()


def upload_large_file(file_path, bucket_name, object_name=None):
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл '{file_path}' не найден.")
        return

    if object_name is None:
        object_name = os.path.basename(file_path)

    file_size_gb = os.path.getsize(file_path) / (1024 ** 3)
    print(f"Размер файла: {file_size_gb:.2f} GB")

    # 1. Инициализация S3-клиента для R2
    s3_client = boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'},
            retries={'max_attempts': 10, 'mode': 'standard'}  # Автоматический повтор при обрывах сети
        )
    )

    # 2. Настройка Multipart Upload (Ключевой момент для файлов > 5 ГБ)
    # Стандарт S3 разрешает максимум 10 000 частей (parts) на один объект.
    # При чанке 64 МБ максимум составит ~640 ГБ. При чанке 128 МБ — до 1.28 ТБ.
    config = TransferConfig(
        multipart_threshold=100 * 1024 * 1024,  # Переключение на multipart если файл > 100 МБ
        max_concurrency=4,  # Количество параллельных потоков загрузки
        multipart_chunksize=64 * 1024 * 1024,  # Размер одного чанка (64 МБ)
        use_threads=True
    )

    print(f"Загрузка файла в бакет '{bucket_name}'...")
    start_time = time.time()
    progress = ProgressPercentage(file_path)

    try:
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=object_name,
            Config=config,
            Callback=progress
        )
        total_time = time.time() - start_time
        print(f"\n\nУспешно загружено за {total_time / 60:.2f} минут!")
    except Exception as e:
        print(f"\n\nОшибка при загрузке: {e}")


if __name__ == "__main__":
    upload_large_file(FILE_PATH, BUCKET_NAME, OBJECT_NAME)