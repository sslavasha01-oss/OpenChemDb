import os
import urllib.parse
import mimetypes
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
    def get_file_response(user_id: int, clean_path: str) -> FileResponse:
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
            "Content-Disposition": f"inline; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"
        }

        return FileResponse(
            path=full_path,
            media_type=media_type,
            headers=headers
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