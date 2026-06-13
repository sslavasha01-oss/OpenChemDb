import io
import mimetypes
import urllib.parse
from datetime import datetime
from pathlib import Path
import shutil

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.core.settings import settings

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".djvu": "image/vnd.djvu",
    ".djv": "image/vnd.djvu",
}


class R2FileManager:
    def __init__(self):
        self.s3_client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            config=Config(signature_version="s3v4"),
        )
        self.bucket_name = settings.R2_BUCKET_NAME

    def _file_exists(self, key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            raise e

    def save_file(self, user_id: int, journal_external_id: str, filename: str, file_bytes: bytes) -> str:
        original_name = Path(filename).name
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix

        base_key_dir = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{journal_external_id}"
        r2_key = f"{base_key_dir}/{original_name}"
        file_name = original_name

        counter = 1
        while self._file_exists(r2_key):
            file_name = f"{stem}_{counter}{suffix}"
            r2_key = f"{base_key_dir}/{file_name}"
            counter += 1

        content_type = MIME_TYPES.get(suffix.lower()) or mimetypes.guess_type(file_name)[
            0] or "application/octet-stream"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name, Key=r2_key, Body=file_bytes, ContentType=content_type
            )
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить файл в R2: {str(e)}")

        return f"{journal_external_id}/{file_name}"

    def get_file_response(self, user_id: int, clean_path: str) -> StreamingResponse:
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{clean_path}"
        try:
            s3_response = self.s3_client.get_object(Bucket=self.bucket_name, Key=r2_key)
        except ClientError as e:
            if e.response['Error']['Code'] == "NoSuchKey":
                raise HTTPException(status_code=404, detail="File not found in R2")
            raise HTTPException(status_code=500, detail=f"Ошибка R2: {str(e)}")

        filename = r2_key.split("/")[-1]
        encoded_filename = urllib.parse.quote(filename)
        content_type = s3_response.get('ContentType', 'application/octet-stream')

        headers = {"Content-Disposition": f"inline; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"}
        return StreamingResponse(content=s3_response['Body'], media_type=content_type, headers=headers)

    def delete_file(self, user_id: int, file_path: str) -> None:
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{file_path}"
        try:
            if self._file_exists(r2_key):
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=r2_key)
        except Exception as e:
            raise RuntimeError(f"Ошибка удаления файла из R2: {str(e)}")

    def clear_user_directory(self, user_id: int) -> None:
        prefix = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/"
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            delete_us = []
            for page in pages:
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if f"/{user_id}/tmp/" in key:
                            continue
                        delete_us.append({'Key': key})
            if delete_us:
                for i in range(0, len(delete_us), 1000):
                    self.s3_client.delete_objects(Bucket=self.bucket_name, Delete={'Objects': delete_us[i:i + 1000]})
        except Exception as e:
            print(f"Ошибка очистки директории R2: {str(e)}")
            raise RuntimeError(f"Ошибка очистки директории R2: {str(e)}")

    def ensure_tmp_dir(self, user_id: int) -> Path:
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        user_tmp_dir = base_user_data_path / str(user_id) / "tmp"
        if user_tmp_dir.exists():
            shutil.rmtree(user_tmp_dir)
        user_tmp_dir.mkdir(parents=True, exist_ok=True)
        return user_tmp_dir

    def save_import_upload(self, user_id: int, file_stream) -> Path:
        user_tmp_dir = self.ensure_tmp_dir(user_id)
        temp_zip_path = user_tmp_dir / f"import_upload_{datetime.utcnow().timestamp()}.zip"
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file_stream, buffer)
        return temp_zip_path

    def extract_attachment_to_disk(self, user_id: int, new_journal_ext_id: str, filename: str, source_stream) -> None:
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{new_journal_ext_id}/{filename}"
        suffix = Path(filename).suffix
        content_type = MIME_TYPES.get(suffix.lower()) or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_bytes = source_stream.read()
        self.s3_client.put_object(Bucket=self.bucket_name, Key=r2_key, Body=file_bytes, ContentType=content_type)

    def copy_file_to_build(self, user_id: int, relative_file_path: str, target_dir: Path) -> None:
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{relative_file_path}"
        filename = r2_key.split("/")[-1]
        try:
            self.s3_client.download_file(Bucket=self.bucket_name, Key=r2_key, Filename=str(target_dir / filename))
        except ClientError:
            pass

    def create_export_archive(self, user_tmp_dir: Path, zip_filename: str, root_build_dir: Path) -> None:
        # Так как zip_filename приходит БЕЗ .zip, archive_base указывает на базовое имя
        archive_base = user_tmp_dir / zip_filename

        # 1. Создаем архив локально (shutil сам добавит .zip на конце)
        shutil.make_archive(str(archive_base), 'zip', root_dir=root_build_dir)

        # 2. Обернем путь к созданному zip в Path объект, чтобы работали .exists() и .unlink()
        local_zip_path = Path(f"{archive_base}.zip")

        # 3. Извлекаем user_id из пути user_tmp_dir (он идет сразу перед /tmp/)
        # Если структура папок: .../{user_id}/tmp, то parts[-2] — это как раз user_id
        user_id = user_tmp_dir.parts[-2]

        # 4. Формируем правильный плоский ключ для R2
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/tmp/{zip_filename}.zip"

        try:
            # 5. Загружаем готовый архив в R2
            self.s3_client.upload_file(
                Filename=str(local_zip_path),
                Bucket=self.bucket_name,
                Key=r2_key,
                ExtraArgs={"ContentType": "application/zip"}
            )
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить архив экспорта в R2: {str(e)}")
        finally:
            # 6. Теперь методы .exists() и .unlink() отработают без ошибок
            if local_zip_path.exists():
                local_zip_path.unlink()

    def get_download_response(self, user_id: int, clean_path: str, disposition: str = "inline", expires_in: int = 900):
        r2_key = f"{settings.R2_USER_DATA_STORAGE_PATH}/{user_id}/{clean_path}"
        if not self._file_exists(r2_key):
            raise HTTPException(status_code=404, detail="File not found in R2")

        filename = r2_key.split("/")[-1]
        encoded_filename = urllib.parse.quote(filename)

        # Определяем заголовок в зависимости от цели
        content_disposition = f"{disposition}; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"

        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': r2_key,
                    'ResponseContentDisposition': content_disposition
                },
                ExpiresIn=expires_in
            )
            return {"url": url}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка R2: {str(e)}")


