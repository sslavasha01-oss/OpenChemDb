import urllib

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from pathlib import Path
from app.core.settings import settings
from typing import List

router = APIRouter(prefix="/files", tags=["Files"])

# Словарь MIME-типов для твоих форматов
MIME_TYPES = {
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".djvu": "image/vnd.djvu",
    ".djv": "image/vnd.djvu",
}


@router.get("/view")
async def view_book_file(file_path: str):
    """
    Отдает файл (PDF, TIFF, DjVu) из папки SOP.
    """
    safe_base = Path(settings.SOP_STORAGE_PATH).resolve()

    # Чистим путь от префикса SOP
    clean_path = file_path.replace("\\", "/")
    if clean_path.startswith("SOP/"):
        clean_path = clean_path[4:]

    full_path = (safe_base / clean_path).resolve()

    # Защита Safe-guard
    if not str(full_path).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Определяем тип файла
    extension = full_path.suffix.lower()
    media_type = MIME_TYPES.get(extension, "application/octet-stream")

    encoded_filename = urllib.parse.quote(full_path.name)

    # Для PDF оставляем inline, для остальных — тоже пробуем inline,
    # но браузер может решить иначе.
    return FileResponse(
        path=full_path,
        media_type=media_type,
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/list", response_model=List[str])
async def list_files_in_directory(dir_path: str):
    """
    Возвращает список всех файлов в указанной директории внутри SOP.
    Пути возвращаются в формате, готовом для эндпоинта /view.
    Пример dir_path: SOP/Яхонтов. Синтетические лекарственные средства
    """
    # 1. Определяем базовый путь (data/SOP)
    safe_base = Path(settings.SOP_STORAGE_PATH).resolve()

    # 2. Очищаем входящий путь от префикса SOP, если он есть
    clean_dir = dir_path.replace("\\", "/")
    if clean_dir.startswith("SOP/"):
        clean_dir = clean_dir[4:]

    # 3. Собираем полный путь к целевой директории
    target_dir = (safe_base / clean_dir).resolve()

    # 4. Проверка безопасности: не даем выйти выше safe_base
    if not str(target_dir).startswith(str(safe_base)):
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    # 5. Проверяем, существует ли директория
    if not target_dir.exists() or not target_dir.is_dir():
        raise HTTPException(status_code=404, detail="Директория не найдена")

    # 6. Сканируем файлы
    files_list = []
    try:
        for entry in target_dir.iterdir():
            if entry.is_file():
                # Формируем путь обратно с префиксом SOP/ для совместимости
                # .relative_to(safe_base.parent) вернет "SOP/каталог/файл.pdf"
                relative_path = entry.relative_to(safe_base.parent)
                files_list.append(str(relative_path).replace("\\", "/"))

        # Сортируем список (полезно для страниц 001, 002...)
        files_list.sort()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при чтении: {str(e)}")

    return files_list