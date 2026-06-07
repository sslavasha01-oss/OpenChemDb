import csv
import io
import zipfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query, Body
from sqlalchemy import select, insert, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.user_journal import canonicalize_molecule_smiles
from app.core.db import get_users_db, users_session_factory
from app.core.settings import settings
from app.models.export import UserExport, ProcessStatus, Type
from app.models.journal_attachment import JournalAttachment
from app.models.user import User
from app.models.user_journal import UserJournal
from app.services.file_manager import FileManager

if settings.LOCAL_MODE:
    FileManager = FileManager
else:
    from app.services.r2_file_manager import R2FileManager
    FileManager = R2FileManager()

router = APIRouter(tags=["export"])


# ------------------------------------------------------------------
# ЕНДПОИНТ 2: ПРОВЕРКА СТАТУСА
# ------------------------------------------------------------------
@router.get("/export-all/status")
async def check_export_status(
        process_type: Type = Query(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Проверяет статус экспорта.
    Если запись отсутствует -> 404 (Не запускался)
    Если path null -> Возвращает статус "processing" (Еще собирается)
    Если path заполнен -> Возвращает сам файл архива (FileResponse)
    """
    stmt = select(UserExport).where(
        UserExport.user_id == current_user.id,
        UserExport.type == process_type)
    result = await db.execute(stmt)
    user_export = result.scalar_one_or_none()

    if not user_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Процесс с типом '{process_type.value}' не запускался или данные устарели."
        )
    return user_export

@router.get("/export-all/download")
async def download_export_archive(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Скачивает готовый ZIP-архив экспорта пользователя на основе пути из БД.
    """
    # 1. Ищем запись об экспорте для текущего пользователя
    stmt = select(UserExport).where(
        UserExport.user_id == current_user.id,
        UserExport.type == Type.EXPORT
    )
    result = await db.execute(stmt)
    user_export = result.scalar_one_or_none()

    if not user_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Экспорт не запускался или данные устарели."
        )

    # 2. Если путь пустой, значит фоновая задача ещё крутится
    if user_export.path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Архив все еще формируется. Пожалуйста, дождитесь завершения операции."
        )

    # 3. Отдаем файл через FileManager, передавая относительный путь (например, "tmp/journal_export.zip")
    try:
        print(current_user.id, user_export.path)
        return FileManager.get_download_response(current_user.id, user_export.path)
    except HTTPException as e:
        # Если FileManager выкинул 404 (файл удален с диска/бакета), превращаем в 410 GONE
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Файл экспорта был удален на сервере. Пожалуйста, запустите экспорт заново."
            )
        raise e

@router.delete("/export-all", status_code=status.HTTP_204_NO_CONTENT)
async def delete_export_data(
        process_type: Type = Query(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Удаляет файл экспорта с диска и очищает запись об экспорте из базы данных.
    """
    # 1. Ищем запись об экспорте для текущего пользователя
    stmt = select(UserExport).where(UserExport.user_id == current_user.id,
                                    UserExport.type == process_type)
    result = await db.execute(stmt)
    user_export = result.scalar_one_or_none()

    if not user_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись об экспорте не найдена."
        )

    # 2. Если файл физически был создан (есть путь), удаляем его через FileManager
    if user_export.path:
        try:
            FileManager.delete_file(current_user.id, user_export.path)
        except Exception as e:
            # Логируем, но продолжаем, чтобы база не осталась в заблокированном/несинхронном состоянии
            print(f"Ошибка при физическом удалении архива экспорта: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Не удалось удалить файл архива с сервера: {str(e)}"
            )

    # 3. Удаляем запись из базы данных
    await db.delete(user_export)
    await db.commit()

    # Так как статус 204 No Content, возвращаем None
    return None

# ------------------------------------------------------------------
# ЕНДПОИНТ 1: ЗАПУСК ЭКСПОРТА (МГНОВЕННЫЙ ОТВЕТ)
# ------------------------------------------------------------------
@router.post("/export-all/start", status_code=status.HTTP_202_ACCEPTED)
async def start_export_user_data(
        background_tasks: BackgroundTasks,
        record_ids: Optional[List[int]] = Query(None, description="Список ID записей для экспорта (?record_ids=1&record_ids=2)"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Инициирует процесс экспорта данных в фоновом режиме.
    Сразу возвращает статус 202 Accepted. Очищает старые файлы экспорта.
    """
    # 1. Синхронно подготавливаем папки через FileManager
    try:
        user_tmp_dir = FileManager.ensure_tmp_dir(current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка подготовки директории экспорта: {str(e)}"
        )
    # Имя будущего файла
    zip_filename = "journal_export"

    # 2. Очищаем/Пересоздаем запись в таблице exports (сбрасываем путь в null, показывая, что процесс идет)
    # Удаляем старую запись, если была
    await db.execute(delete(UserExport).where(UserExport.user_id == current_user.id))
    # Создаем новую «пустую» запись (path=None означает, что экспорт в процессе обработки)
    new_export = UserExport(user_id=current_user.id, path=None, type=Type.EXPORT)
    db.add(new_export)
    await db.commit()

    # 3. Ставим тяжелую задачу архивации в бэкграунд FastAPI
    background_tasks.add_task(
        background_export_task,
        user_id=current_user.id,
        user_tmp_dir=user_tmp_dir,
        zip_filename=zip_filename,
        record_ids=record_ids
    )

    return {"status": "processing", "message": "Экспорт данных запущен в фоновом режиме."}

# ------------------------------------------------------------------
# ФОНОВАЯ ФУНКЦИЯ ДЛЯ ВЫПОЛНЕНИЯ ЭКСПОРТА
# ------------------------------------------------------------------
async def background_export_task(user_id: int, user_tmp_dir: Path, zip_filename: str, record_ids: Optional[List[int]] = None):
    """
    Тяжелая фоновая задача, которая собирает файлы и делает ZIP.
    В конце обновляет путь в таблице exports.
    """
    # Открываем новую изолированную сессию БД для фонового потока
    async with users_session_factory() as db:
        try:
            with TemporaryDirectory() as temp_build_dir:
                build_path = Path(temp_build_dir)
                attachments_build_dir = build_path / "attachments"
                attachments_build_dir.mkdir(parents=True, exist_ok=True)

                # Имя архива и путь
                final_zip_path = user_tmp_dir / f"{zip_filename}.zip"

                # 1. ЖУРНАЛ
                journal_stmt = select(UserJournal).where(UserJournal.user_id == user_id).order_by(
                    UserJournal.external_id)
                if record_ids:
                    journal_stmt = journal_stmt.where(UserJournal.id.in_(record_ids))
                journal_result = await db.execute(journal_stmt)
                journal_records = journal_result.scalars().all()

                journal_data = []
                journal_headers = []

                if journal_records:
                    columns = UserJournal.__table__.columns.keys()
                    filtered_cols = [c for c in columns if c not in ("id", "user_id") and not c.endswith("_mol_data")]
                    if "external_id" in filtered_cols:
                        filtered_cols.remove("external_id")
                        journal_headers = ["external_id"] + filtered_cols
                    else:
                        journal_headers = filtered_cols

                    for rec in journal_records:
                        row = {col: getattr(rec, col) for col in journal_headers}
                        journal_data.append(row)

                journal_tsv_path = build_path / "journal.tsv"
                with open(journal_tsv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=journal_headers, delimiter="\t")
                    writer.writeheader()
                    writer.writerows(journal_data)

                # 2. АТТАЧМЕНТЫ
                attach_stmt = select(JournalAttachment).where(JournalAttachment.user_id == user_id)
                if record_ids:
                    # Фильтруем аттачменты, завязанные на journal_record_id из списка разрешенных
                    attach_stmt = attach_stmt.where(JournalAttachment.journal_record_id.in_(record_ids))
                attach_result = await db.execute(attach_stmt)
                attach_records = attach_result.scalars().all()

                attach_data = []
                attach_headers = []

                if attach_records:
                    attach_columns = JournalAttachment.__table__.columns.keys()
                    filtered_attach_cols = [c for c in attach_columns if c not in ("id", "user_id", "journal_record_id")]
                    attach_headers = filtered_attach_cols

                    for attach in attach_records:
                        row = {col: getattr(attach, col) for col in attach_headers}
                        attach_data.append(row)

                        relative_file_path = attach.file_path
                        journal_ext_id = relative_file_path.split("/")[0]
                        target_file_dir = attachments_build_dir / journal_ext_id
                        target_file_dir.mkdir(parents=True, exist_ok=True)

                        FileManager.copy_file_to_build(user_id, relative_file_path, target_file_dir)

                attachments_tsv_path = build_path / "attachments.tsv"
                with open(attachments_tsv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=attach_headers, delimiter="\t")
                    writer.writeheader()
                    writer.writerows(attach_data)

                # 3. УПАКОВКА В ZIP через FileManager
                FileManager.create_export_archive(user_tmp_dir, zip_filename, build_path)

            # 4. ОБНОВЛЕНИЕ СТАТУСА В БД ПОСЛЕ УСПЕШНОГО ЗАВЕРШЕНИЯ
            db_relative_path = f"tmp/{zip_filename}.zip"
            stmt = (
                update(UserExport)
                .where(UserExport.user_id == user_id,
                       UserExport.type == Type.EXPORT)
                .values(path=db_relative_path, created_date=datetime.utcnow())
            )
            await db.execute(stmt)
            await db.commit()

        except Exception as e:

            stmt = (
                update(UserExport)
                .where(UserExport.user_id == user_id,
                       UserExport.type == Type.EXPORT)
                .values(error_message= 'error', path=db_relative_path, created_date=datetime.utcnow())
            )
            print(f"Ошибка фонового экспорта для пользователя {user_id}: {str(e)}")
            await db.execute(stmt)
            await db.commit()


@router.post("/import/start", status_code=status.HTTP_202_ACCEPTED)
async def start_import_user_data(
        replace: bool = Form(False),
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    # Проверяем, нет ли уже запущенных процессов импорта или экспорта
    status_stmt = select(UserExport).where(UserExport.user_id == current_user.id)
    res = await db.execute(status_stmt)
    active_process = res.scalar_one_or_none()

    if active_process and active_process.status in (ProcessStatus.PROCESSING_IMPORT, ProcessStatus.PROCESSING_EXPORT):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"База данных заблокирована. Сейчас выполняется операция: {active_process.status.value}"
        )

    # Сохраняем загруженный ZIP файл через FileManager во временную директорию
    try:
        temp_zip_path = FileManager.save_import_upload(current_user.id, file.file)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл на сервере: {str(e)}")
    finally:
        await file.close()

    # Устанавливаем блокировку импорта
    if active_process:
        await db.execute(delete(UserExport).where(UserExport.user_id == current_user.id and UserExport.type == Type.IMPORT))

    new_lock = UserExport(user_id=current_user.id, type=Type.IMPORT, status=ProcessStatus.PROCESSING_IMPORT, path=None)
    db.add(new_lock)
    await db.commit()

    # Запускаем фоновый импорт
    background_tasks.add_task(
        background_import_task,
        user_id=current_user.id,
        temp_zip_path=temp_zip_path,
        replace=replace
    )

    return {"status": "processing", "message": "Импорт данных успешно запущен в фоновом режиме. База заблокирована."}


async def background_import_task(
        user_id: int,
        temp_zip_path: Path,
        replace: bool
):
    extracted_files = []
    try:
        # Открываем архив внутри try

        with zipfile.ZipFile(temp_zip_path, "r") as archive:
            namelist = archive.namelist()

            # Шаг 1: Очистка старых данных (если replace=True)
            if replace:
                async with users_session_factory() as db:
                    await db.execute(delete(JournalAttachment).where(JournalAttachment.user_id == user_id))
                    await db.execute(delete(UserJournal).where(UserJournal.user_id == user_id))
                    await db.commit()

                # Очищаем файлы на диске через FileManager
                FileManager.clear_user_directory(user_id)

            async with users_session_factory() as db:
                # 2. ИМПОРТ ЖУРНАЛА
                old_to_new_ext_id = {}
                with archive.open("journal.tsv") as tsv_file:
                    text_stream = io.TextIOWrapper(tsv_file, encoding="utf-8")
                    reader = csv.DictReader(text_stream, delimiter="\t")

                    for row in reader:
                        old_ext_id = int(row.pop("external_id"))

                        data = {
                            k: v for k, v in row.items()
                            if v not in (None, "") and k not in ('id', 'product_svg')
                        }

                        insert_data = {}
                        for key, value in data.items():
                            if key.endswith('_mol_data') or key in ('reaction_mol_data', 'reaction_mol_mapped_data'):
                                continue
                            insert_data[key] = value

                        for date_field in ('date_added', 'date_modified'):
                            if data.get(date_field):
                                try:
                                    insert_data[date_field] = datetime.fromisoformat(data[date_field])
                                except ValueError:
                                    insert_data.pop(date_field, None)

                        # Молекулярная магия RDKit
                        if data.get('product_smiles'):
                            canon_smi = canonicalize_molecule_smiles(data['product_smiles'])
                            insert_data['product_smiles'] = canon_smi
                            insert_data['product_mol_data'] = func.mol_from_smiles(canon_smi) if canon_smi else None

                        for i in range(1, 6):
                            smiles_key = f'reagent{i}_smiles'
                            mol_key = f'reagent{i}_mol_data'
                            if data.get(smiles_key):
                                canon_smi = canonicalize_molecule_smiles(data[smiles_key])
                                insert_data[smiles_key] = canon_smi
                                insert_data[mol_key] = func.mol_from_smiles(canon_smi) if canon_smi else None

                        if data.get('reaction_smiles'):
                            insert_data['reaction_mol_data'] = func.reaction_from_smiles(data['reaction_smiles'])
                        if data.get('reaction_mapped_smiles'):
                            insert_data['reaction_mol_mapped_data'] = func.reaction_from_smiles(
                                data['reaction_mapped_smiles'])

                        insert_data['user_id'] = user_id

                        stmt = insert(UserJournal).values(**insert_data).returning(UserJournal.id,
                                                                                   UserJournal.external_id)
                        res = await db.execute(stmt)
                        new_id, new_ext_id = res.fetchone()
                        # Сохраняем словарь с обоими айдишниками
                        old_to_new_ext_id[old_ext_id] = {"new_id": new_id, "new_ext_id": new_ext_id}

                # Подготовка аттачментов для БД (БЕЗ копирования файлов)
                attachments_to_insert = []
                if "attachments.tsv" in namelist:
                    with archive.open("attachments.tsv") as tsv_file:
                        text_stream = io.TextIOWrapper(tsv_file, encoding="utf-8")
                        reader = csv.DictReader(text_stream, delimiter="\t")

                        for row in reader:
                            old_journal_ext_id = int(row.get("journal_record_ext_id"))
                            if old_journal_ext_id not in old_to_new_ext_id:
                                continue

                            new_journal_ext_id = old_to_new_ext_id[old_journal_ext_id]["new_ext_id"]

                            clean_row = {k: (v if v != "" else None) for k, v in row.items() if k != 'id'}
                            clean_row["user_id"] = user_id
                            clean_row["journal_record_ext_id"] = new_journal_ext_id

                            if clean_row.get("date_added"):
                                try:
                                    clean_row["date_added"] = datetime.fromisoformat(clean_row["date_added"])
                                except ValueError:
                                    clean_row["date_added"] = datetime.utcnow()

                            file_name = clean_row["file_path"].split("/")[-1]
                            clean_row["file_path"] = f"{new_journal_ext_id}/{file_name}"

                            attachments_to_insert.append((clean_row, old_journal_ext_id, new_journal_ext_id, file_name))

                        # Если есть аттачменты — привязываем их к journal_record_id напрямую из словаря
                        if attachments_to_insert:
                            db_attachments = []
                            for att_row, old_ext, new_ext, f_name in attachments_to_insert:
                                # Достаем внутренний id записи из нашего маппинга по old_ext
                                att_row["journal_record_id"] = old_to_new_ext_id[old_ext]["new_id"]
                                db_attachments.append(att_row)

                            await db.execute(insert(JournalAttachment), db_attachments)

                        # Шаг 3: Физическое копирование файлов на диск (строго внутри сессии до коммита)
                        if attachments_to_insert:
                            for att_row, old_ext, new_ext, f_name in attachments_to_insert:
                                zip_file_path = f"attachments/{old_ext}/{f_name}"
                                if zip_file_path in namelist:
                                    with archive.open(zip_file_path) as source_file:
                                        FileManager.extract_attachment_to_disk(
                                            user_id=user_id,
                                            new_journal_ext_id=new_ext,
                                            filename=f_name,
                                            source_stream=source_file
                                        )
                                        extracted_files.append((new_ext, f_name))

                await db.commit()
            # Снимаем блокировку импорта
            async with users_session_factory() as db:
                await db.execute(
                    update(UserExport)
                    .where(UserExport.user_id == user_id and UserExport.type == Type.IMPORT)
                    .values(status=ProcessStatus.COMPLETED)
                )
                await db.commit()

    except Exception as e:
        # Если упали — пишем статус FAILED
        if 'extracted_files' in locals() and extracted_files:
            for n_ext, f_name in extracted_files:
                try:
                    FileManager.delete_file(user_id, str(n_ext) + '/' + f_name)
                except Exception:
                    pass
        async with users_session_factory() as db:
            stmt = (
                update(UserExport)
                .where(UserExport.user_id == user_id and UserExport.type == Type.IMPORT)
                .values(status=ProcessStatus.FAILED, error_message=str(e))
            )
            await db.execute(stmt)
            await db.commit()

    finally:
        if temp_zip_path.exists():
            try:
                temp_zip_path.unlink()
            except PermissionError:
                # На крайний случай, если у ОС жесткий затуп с кэшем дескрипторов
                import gc
                import time
                gc.collect()
                time.sleep(0.1)
                try:
                    temp_zip_path.unlink()
                except Exception:
                    pass