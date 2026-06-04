import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.db import get_users_db
from app.core.settings import settings
from app.models.journal_attachment import JournalAttachment, AttachmentType
from app.models.user import User
from app.models.user_journal import UserJournal
from app.schemas.jounal_attachment import JournalAttachmentResponseSchema
from fastapi.responses import FileResponse
import urllib.parse
from fastapi import status
import mimetypes
from app.services.thumbnails import generate_image_thumbnail, generate_video_thumbnail

router = APIRouter(prefix="/journal_attachment", tags=["journal attachment"])

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".djvu": "image/vnd.djvu",
    ".djv": "image/vnd.djvu",
}


@router.post("/upload", response_model=JournalAttachmentResponseSchema)
async def upload_journal_attachment(
        journal_record_id: int = Form(...),
        attachment_type: AttachmentType = Form(...),
        description: str = Form(None),
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Загружает файл аттачмента, сохраняет его в user_data/{user_id}/{journal_record_external_id}/{file_name}
    и делает запись в таблицу journal_attachment.
    """
    print(file.size)
    if file.size > settings.MAX_FILE_SIZE:
        max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,  # 413 Payload Too Large
            detail=f"Файл слишком большой. Максимально допустимый размер: {max_mb:.0f} МБ."
        )
    # 1. Проверяем, существует ли запись в журнале и принадлежит ли она текущему пользователю
    query = select(UserJournal).where(
        UserJournal.id == journal_record_id,
        UserJournal.user_id == current_user.id
    )
    result = await db.execute(query)
    journal_record = result.scalar_one_or_none()

    if not journal_record:
        raise HTTPException(
            status_code=404,
            detail="Запись в журнале не найдена или у вас нет к ней доступа."
        )

    # Получаем external_id из найденной записи
    journal_external_id = journal_record.external_id

    # 2. Формируем пути для сохранения файла
    # 2. Формируем пути для сохранения файла
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()

    # Безопасное оригинальное имя файла (без путей вроде ../../etc/passwd)
    original_file_name = Path(file.filename).name

    # Полная директория: user_data/{user_id}/{journal_record_external_id}/
    target_dir = base_user_data_path / str(current_user.id) / str(journal_external_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    # --- ЛОГИКА УНИКАЛИЗАЦИИ ИМЕНИ ФАЙЛА ---
    full_file_path = target_dir / original_file_name
    file_name = original_file_name

    if full_file_path.exists():
        stem = Path(original_file_name).stem  # Имя файла без расширения (например, "photo")
        suffix = Path(original_file_name).suffix  # Расширение (например, ".jpg")
        counter = 1

        # Цикл работает, пока не найдет свободное имя
        while full_file_path.exists():
            file_name = f"{stem}_{counter}{suffix}"
            full_file_path = target_dir / file_name
            counter += 1
    # ----------------------------------------

    # 3. Сохраняем файл на диск асинхронно-блочным способом
    # 3. Читаем байты (они пригодятся, если это картинка) и сохраняем файл на диск
    try:
        file_bytes = await file.read()  # Читаем асинхронно байты

        with open(full_file_path, "wb") as buffer:
            buffer.write(file_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")
    finally:
        await file.close()

    # 4. Формируем относительный путь для сохранения в БД
    db_file_path = f"{journal_external_id}/{file_name}"

    # --- КРОССПЛАТФОРМЕННАЯ ГЕНЕРАЦИЯ ПРЕВЬЮ ---
    thumbnail_data = None
    if attachment_type == AttachmentType.MEDIA:
        # Так как физического файла для mimetypes еще может не быть (или он в S3),
        # определяем тип по оригинальному имени файла, который прислал фронт
        mime_type, _ = mimetypes.guess_type(file.filename)

        if mime_type:
            if mime_type.startswith("image/"):
                thumbnail_data = generate_image_thumbnail(file_bytes)
            elif mime_type.startswith("video/"):
                # Передаем байты, а не путь!
                thumbnail_data = generate_video_thumbnail(file_bytes)

    # 5. Записываем информацию в таблицу journal_attachment
    print(journal_external_id)
    new_attachment = JournalAttachment(
        user_id=current_user.id,
        journal_record_id=journal_record_id,
        journal_record_ext_id=journal_external_id,
        type=attachment_type,
        description=description,
        file_path=db_file_path,
        thumbnail_b64=thumbnail_data  # Сохраняем строку Base64
    )

    db.add(new_attachment)
    await db.commit()
    await db.refresh(new_attachment)

    return new_attachment


@router.get("/view-user-file")
async def view_user_file(
        file_path: str,  # Ожидаем формат: "external_id/filename.ext"
        current_user: User = Depends(get_current_user)
):
    """
    Отдает файл из папки user_data/{user_id}/{file_path}.
    Путь строится на основе ID пользователя из токена.
    """
    safe_base = Path(settings.USER_DATA_STORAGE_PATH).resolve()

    # Чистим пришедший путь от возможных лишних префиксов
    clean_path = file_path.replace("\\", "/")
    if clean_path.startswith("user_data/"):
        clean_path = clean_path[10:]

    # Собираем путь: user_data / {user_id} / {external_id}/{filename}
    # Строго подставляем ID из токена, фронт не может подсмотреть чужой файл
    full_path = (safe_base / str(current_user.id) / clean_path).resolve()

    # Защита Safe-guard от Path Traversal (чтобы нельзя было через ../ выйти наружу)
    # Ограничиваем область видимости папкой конкретного юзера
    user_safe_zone = safe_base / str(current_user.id)
    if not str(full_path).startswith(str(user_safe_zone.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    # Проверяем физическое существование файла
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # --- УЛУЧШЕННОЕ ОПРЕДЕЛЕНИЕ MIME-ТИПА ---
    extension = full_path.suffix.lower()

    # Сначала смотрим в кастомный словарь, если там нет — используем стандартный mimetypes
    media_type = MIME_TYPES.get(extension)
    if not media_type:
        media_type, _ = mimetypes.guess_type(full_path)
    if not media_type:
        media_type = "application/octet-stream"

    # --- КОРРЕКТНОЕ ИМЯ ДЛЯ СКАЧИВАНИЯ ---
    filename = full_path.name
    encoded_filename = urllib.parse.quote(filename)

    # Используем правильный формат Content-Disposition.
    # Если это картинка или видео, inline заставит браузер показать её прямо в теге/вкладке,
    # но если юзер нажмет "Сохранить как...", браузер возьмет имя из filename*
    headers = {
        "Content-Disposition": f"inline; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}"
    }

    return FileResponse(
        path=full_path,
        media_type=media_type,
        headers=headers
    )

# Схема для входных данных
class UpdateAttachmentDescriptionSchema(BaseModel):
    description: Optional[str] = None

@router.patch("/{attachment_id}", response_model=JournalAttachmentResponseSchema)
async def update_attachment_description(
    attachment_id: int,
    data: UpdateAttachmentDescriptionSchema,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_users_db)
):
    """
    Обновляет только поле description у аттачмента.
    """
    # Ищем аттачмент в базе данных и проверяем владельца
    query = select(JournalAttachment).where(
        JournalAttachment.id == attachment_id,
        JournalAttachment.user_id == current_user.id
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=404,
            detail="Аттачмент не найден или у вас нет прав на его изменение."
        )

    # Обновляем только описание
    attachment.description = data.description

    await db.commit()
    await db.refresh(attachment)

    return attachment


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
        attachment_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Удаляет файл аттачмента с диска и запись о нем из базы данных.
    """
    # 1. Ищем аттачмент в базе и проверяем права
    query = select(JournalAttachment).where(
        JournalAttachment.id == attachment_id,
        JournalAttachment.user_id == current_user.id
    )
    result = await db.execute(query)
    attachment = result.scalar_one_or_none()

    if not attachment:
        raise HTTPException(
            status_code=404,
            detail="Аттачмент не найден или у вас нет прав на его удаление."
        )

    # 2. Формируем полный путь к файлу на сервере
    # Напоминание: в базе file_path хранится как "{external_id}/{file_name}"
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
    full_file_path = base_user_data_path / str(current_user.id) / attachment.file_path

    # Безопасность: проверяем, что путь не вышел за пределы папки user_data
    if not str(full_file_path.resolve()).startswith(str(base_user_data_path)):
        raise HTTPException(status_code=403, detail="Попытка удаления системного файла отклонена")

    # 3. Физически удаляем файл с диска
    try:
        if full_file_path.exists() and full_file_path.is_file():
            os.remove(full_file_path)

            # Опционально: удаляем пустую папку (external_id), если в ней больше нет файлов
            parent_dir = full_file_path.parent
            if parent_dir.exists() and not os.listdir(parent_dir):
                parent_dir.rmdir()

    except Exception as e:
        # Логируем ошибку, но можно выбросить HTTPException, если критично не удалять из БД при сбое диска
        print(f"Ошибка при удалении файла с диска: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось удалить файл с сервера: {str(e)}"
        )

    # 4. Удаляем запись из базы данных
    await db.delete(attachment)
    await db.commit()

    # Так как статус 204 No Content, тело ответа возвращать не нужно
    return None

# Схема для тела запроса (передаем список ID)
class FetchAttachmentsRequestSchema(BaseModel):
    journal_record_ids: List[int]

# Структура группировки внутри одной записи журнала
class GroupedAttachmentsSchema(BaseModel):
    ARTICLE: List[JournalAttachmentResponseSchema] = []
    SPECTRUM: List[JournalAttachmentResponseSchema] = []
    MEDIA: List[JournalAttachmentResponseSchema] = []

# Финальный формат ответа: { "id_записи": { "ARTICLE": [...], "SPECTRUM": [...] } }
# Использование Dict[int, ...] автоматически превратит ключи в строки/числа в JSON
class BatchAttachmentsResponseSchema(BaseModel):
    attachments: Dict[int, GroupedAttachmentsSchema]


@router.post("/batch", response_model=BatchAttachmentsResponseSchema)
async def get_batch_attachments(
        data: FetchAttachmentsRequestSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Принимает список ID записей журнала и возвращает аттачменты,
    сгруппированные по journal_record_id и по типам (ARTICLE, SPECTRUM).
    Возвращает данные только для тех записей, которые принадлежат текущему пользователю.
    """
    if not data.journal_record_ids:
        return {"attachments": {}}

    # 1. Запрашиваем аттачменты только для переданных ID и строго для текущего пользователя (security check)
    query = select(JournalAttachment).where(
        JournalAttachment.journal_record_id.in_(data.journal_record_ids),
        JournalAttachment.user_id == current_user.id
    )
    result = await db.execute(query)
    attachments = result.scalars().all()

    # 2. Инициализируем пустую структуру для ответа, чтобы фронтенд получил пустые списки,
    # даже если для какого-то переданного ID файлов вообще не нашлось.
    result_dict = {
        record_id: {"ARTICLE": [], "SPECTRUM": [], "MEDIA": []}
        for record_id in data.journal_record_ids
    }

    # 3. Распределяем полученные из БД аттачменты по группам
    for att in attachments:
        rec_id = att.journal_record_id
        att_type = att.type.value if hasattr(att.type, 'value') else str(att.type)  # Обработка Enum

        if rec_id in result_dict and att_type in result_dict[rec_id]:
            result_dict[rec_id][att_type].append(att)

    return {"attachments": result_dict}