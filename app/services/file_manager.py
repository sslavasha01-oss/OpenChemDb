import os
import shutil
import urllib.parse
import mimetypes
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse
from app.core.settings import settings

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".djvu": "image/vnd.djvu",
    ".djv": "image/vnd.djvu",
}

class FileManager:

    @staticmethod
    def save_file(user_id: int, journal_external_id: str, filename: str, file_bytes: bytes) -> str:
        """
        Сохраняет файл на локальный диск, обрабатывая уникализацию имён.
        Возвращает относительный путь для сохранения в БД: 'external_id/filename.ext'
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        original_file_name = Path(filename).name

        # Полная директория: user_data/{user_id}/{journal_record_external_id}/
        target_dir = base_user_data_path / str(user_id) / str(journal_external_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        full_file_path = target_dir / original_file_name
        file_name = original_file_name

        # Логика уникализации имени файла
        if full_file_path.exists():
            stem = Path(original_file_name).stem
            suffix = Path(original_file_name).suffix
            counter = 1

            while full_file_path.exists():
                file_name = f"{stem}_{counter}{suffix}"
                full_file_path = target_dir / file_name
                counter += 1

        with open(full_file_path, "wb") as buffer:
            buffer.write(file_bytes)

        return f"{journal_external_id}/{file_name}"

    @staticmethod
    def get_file_response(user_id: int, clean_path: str, disposition: str = "inline") -> FileResponse:
        """
        Проверяет безопасность пути, существование файла и возвращает FileResponse.
        """
        safe_base = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        full_path = (safe_base / str(user_id) / clean_path).resolve()

        # Защита от Path Traversal
        user_safe_zone = safe_base / str(user_id)
        if not str(full_path).startswith(str(user_safe_zone.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        if not full_path.exists() or not full_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Определение MIME-типа
        extension = full_path.suffix.lower()
        media_type = MIME_TYPES.get(extension)
        if not media_type:
            media_type, _ = mimetypes.guess_type(full_path)
        if not media_type:
            media_type = "application/octet-stream"

        # Формирование заголовков скачивания
        filename = full_path.name
        encoded_filename = urllib.parse.quote(filename)
        headers = {
            "Content-Disposition": f"inline; filename=\"{encoded_filename}\"; filename*=UTF-8''{encoded_filename}"
        }

        return FileResponse(
            path=full_path,
            media_type=media_type,
            filename=encoded_filename,
            content_disposition_type=disposition  # 'inline' или 'attachment'
        )

    @staticmethod
    def delete_file(user_id: int, file_path: str) -> None:
        """
        Удаляет файл с диска и очищает пустую папку записи, если она осталась пустой.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        full_file_path = base_user_data_path / str(user_id) / file_path

        if not str(full_file_path.resolve()).startswith(str(base_user_data_path)):
            raise HTTPException(status_code=403, detail="Попытка удаления системного файла отклонена")

        if full_file_path.exists() and full_file_path.is_file():
            os.remove(full_file_path)

            # Удаляем пустую папку (external_id), если в ней больше нет файлов
            parent_dir = full_file_path.parent
            if parent_dir.exists() and not os.listdir(parent_dir):
                parent_dir.rmdir()

    @staticmethod
    def clear_user_directory(user_id: int) -> None:
        """
        Удаляет все файлы и папки пользователя на диске, кроме папки 'tmp'.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        user_dir = base_user_data_path / str(user_id)

        if user_dir.exists():
            for item in user_dir.iterdir():
                if item.is_dir() and item.name == "tmp":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    @staticmethod
    def ensure_tmp_dir(user_id: int) -> Path:
        """
        Очищает и пересоздает временную директорию 'tmp' для пользователя.
        Возвращает путь к ней.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        user_tmp_dir = base_user_data_path / str(user_id) / "tmp"

        if user_tmp_dir.exists():
            shutil.rmtree(user_tmp_dir)
        user_tmp_dir.mkdir(parents=True, exist_ok=True)
        return user_tmp_dir

    @staticmethod
    def save_import_upload(user_id: int, file_stream) -> Path:
        """
        Сохраняет входящий поток UploadFile во временную папку для фонового импорта.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        user_tmp_dir = base_user_data_path / str(user_id) / "tmp"
        user_tmp_dir.mkdir(parents=True, exist_ok=True)

        temp_zip_path = user_tmp_dir / f"import_upload_{datetime.utcnow().timestamp()}.zip"
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file_stream, buffer)
        return temp_zip_path

    @staticmethod
    def extract_attachment_to_disk(user_id: int, new_journal_ext_id: str, filename: str, source_stream) -> None:
        """
        Извлекает поток файла из архива и сохраняет в целевую папку записи.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        target_dir = base_user_data_path / str(user_id) / str(new_journal_ext_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        with open(target_dir / filename, "wb") as target_file:
            shutil.copyfileobj(source_stream, target_file)

    @staticmethod
    def copy_file_to_build(user_id: int, relative_file_path: str, target_dir: Path) -> None:
        """
        Копирует файл из хранилища пользователя во временную сборочную директорию экспорта.
        """
        base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
        source_file_path = base_user_data_path / str(user_id) / relative_file_path

        if source_file_path.exists() and source_file_path.is_file():
            shutil.copy2(source_file_path, target_dir / source_file_path.name)

    @staticmethod
    def create_export_archive(user_tmp_dir: Path, zip_filename: str, root_build_dir: Path) -> None:
        """
        Упаковывает собранную директорию в ZIP архив.
        """
        archive_base = user_tmp_dir / zip_filename
        shutil.make_archive(str(archive_base), 'zip', root_dir=root_build_dir)

    @staticmethod
    def get_download_response(user_id: int, clean_path: str, disposition: str = "inline") -> dict:
        """
        Локальный режим: возвращает URL на эндпоинт просмотра файлов.
        """
        # Формируем относительный URL для локального скачивания
        local_url = f"/api/journal_attachment/view-user-file?file_path={clean_path}"
        return {"url": local_url}