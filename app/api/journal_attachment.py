import mimetypes
import urllib
from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi import status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_users_db
from app.core.settings import settings
from app.models.journal_attachment import JournalAttachment, AttachmentType
from app.models.user import User
from app.models.user_journal import UserJournal
from app.schemas.jounal_attachment import JournalAttachmentResponseSchema
from app.services.file_manager import FileManager
from app.services.thumbnails import generate_image_thumbnail, generate_video_thumbnail

if settings.LOCAL_MODE:
    FileManager = FileManager
else:
    from app.services.r2_file_manager import R2FileManager
    FileManager = R2FileManager()

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
    if not settings.LOCAL_MODE:
        if file.size > settings.MAX_FILE_SIZE:
            max_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=413,  # 413 Payload Too Large
                detail=f"File is too large. Maximum allowed: {max_mb:.0f} MB."
            )
        # Проверка общего лимита пользователя по его тарифу
        user_tariff = getattr(current_user, "tariff_plan")
        max_allowed_total = settings.TARIFF_LIMITS.get(user_tariff, settings.TARIFF_LIMITS["FREE"])
        current_total = getattr(current_user, "attachments_total_size")
        if current_total + file.size > max_allowed_total:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough space in cloud. Current tariff: {user_tariff}. Available: {(max_allowed_total - current_total) / (1024 * 1024):.1f} MB."
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

    # 2. Читаем байты файла (для сохранения и генерации превью)
    try:
        file_bytes = await file.read()

        # 3. Сохраняем файл через универсальный FileManager
        db_file_path = FileManager.save_file(
            user_id=current_user.id,
            journal_external_id=journal_external_id,
            filename=file.filename,
            file_bytes=file_bytes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")
    finally:
        await file.close()

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
    new_attachment = JournalAttachment(
        user_id=current_user.id,
        journal_record_id=journal_record_id,
        journal_record_ext_id=journal_external_id,
        type=attachment_type,
        description=description,
        file_path=db_file_path,
        thumbnail_b64=thumbnail_data,
        file_size=file.size
    )

    db.add(new_attachment)
    current_user.attachments_total_size += file.size
    db.add(current_user)
    await db.commit()
    await db.refresh(new_attachment)

    return new_attachment


@router.get("/view-user-file")
async def view_user_file(
        file_path: str,  # Ожидаем формат: "external_id/filename.ext"
        disposition: str = "inline",
        current_user: User = Depends(get_current_user)
):
    """
    Отдает файл из папки user_data/{user_id}/{file_path}.
    Путь строится на основе ID пользователя из токена.
    """
    # Чистим пришедший путь от возможных лишних префиксов
    clean_path = file_path.replace("\\", "/")
    if clean_path.startswith("user_data/"):
        clean_path = clean_path[10:]

    # Делегируем логику проверки и отдачи ответа менеджеру файлов
    return FileManager.get_file_response(current_user.id, clean_path, disposition=disposition)

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

    # 2. Физически удаляем файл с помощью FileManager
    try:
        FileManager.delete_file(current_user.id, attachment.file_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось удалить файл с сервера: {str(e)}"
        )
    attachment_size = attachment.file_size or 0

    # Вычитаем размер, не уходя в минус
    current_user.attachments_total_size = max(0, current_user.attachments_total_size - attachment_size)
    db.add(current_user)

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


@router.get("/get-download-url")
async def get_attachment_url(
        file_path: str,
        disposition: str = "inline",  # "inline" для просмотра, "attachment" для скачивания
        current_user: User = Depends(get_current_user)
):
    # Чистим путь
    clean_path = file_path.replace("\\", "/").replace("user_data/", "")

    # Получаем URL (подписанный для R2 или локальный путь)
    return FileManager.get_download_response(current_user.id, clean_path, disposition=disposition)