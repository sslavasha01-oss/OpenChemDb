import csv
import io
import shutil
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy import select, insert, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.user_journal import canonicalize_molecule_smiles
from app.core.db import get_users_db, users_session_factory
from app.core.settings import settings
from app.models.export import UserExport, ProcessStatus
from app.models.journal_attachment import JournalAttachment
from app.models.user import User
from app.models.user_journal import UserJournal

router = APIRouter(tags=["export"])


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_user_data(
        replace: bool = Form(False),
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Импортирует данные пользователя из ZIP-архива.
    Поддерживает режим replace=True (полная очистка старых данных) и replace=False (добавление).
    """
    user_id_str = str(current_user.id)
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
    user_dir = base_user_data_path / user_id_str

    # 1. Читаем архив в память
    try:
        archive_bytes = await file.read()
        zip_buffer = io.BytesIO(archive_bytes)

        if not zipfile.is_zipfile(zip_buffer):
            raise HTTPException(status_code=400, detail="Загруженный файл не является валидным ZIP-архивом.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка чтения файла: {str(e)}")
    finally:
        await file.close()

    # 2. Обработка режима REPLACE (Очистка)
    if replace:
        try:
            # Удаляем записи из БД (каскадно или вручную обе таблицы)
            # Сначала аттачменты, потом журнал
            await db.execute(delete(JournalAttachment).where(JournalAttachment.user_id == current_user.id))
            await db.execute(delete(UserJournal).where(UserJournal.user_id == current_user.id))
            await db.commit()

            # Удаляем файлы на диске, КРОМЕ папки tmp (если она вдруг там есть)
            if user_dir.exists():
                for item in user_dir.iterdir():
                    if item.is_dir() and item.name == "tmp":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка при очистке старых данных: {str(e)}")

    # Контекст для работы с ZIP
    with zipfile.ZipFile(zip_buffer, "r") as archive:
        namelist = archive.namelist()

        if "journal.tsv" not in namelist:
            raise HTTPException(status_code=400, detail="В архиве отсутствует обязательный файл journal.tsv")

        # ------------------------------------------------------------------
        # 3. ИМПОРТ ЖУРНАЛА (С ручной канонизацией и генерацией функций RDKit)
        # ------------------------------------------------------------------
        old_to_new_ext_id = {}  # Маппинг { old_external_id: new_external_id }

        try:
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
                        # Игнорируем молекулярные поля, если они вдруг есть в файле
                        if key.endswith('_mol_data') or key in ('reaction_mol_data', 'reaction_mol_mapped_data'):
                            continue
                        insert_data[key] = value

                    # --- ПАРСИНГ ДАТ ЖУРНАЛА ДЛЯ СОХРАНЕНИЯ ИСТОРИИ ---
                    for date_field in ('date_added', 'date_modified'):
                        if data.get(date_field):
                            try:
                                insert_data[date_field] = datetime.fromisoformat(data[date_field])
                            except ValueError:
                                # Если дата некорректная, удаляем ключ, чтобы СУБД поставила дефолт сама
                                insert_data.pop(date_field, None)

                    # Продукт
                    if data.get('product_smiles'):
                        canon_smi = canonicalize_molecule_smiles(data['product_smiles'])
                        insert_data['product_smiles'] = canon_smi
                        insert_data['product_mol_data'] = func.mol_from_smiles(canon_smi) if canon_smi else None

                    # Реагенты 1-5
                    for i in range(1, 6):
                        smiles_key = f'reagent{i}_smiles'
                        mol_key = f'reagent{i}_mol_data'
                        if data.get(smiles_key):
                            canon_smi = canonicalize_molecule_smiles(data[smiles_key])
                            insert_data[smiles_key] = canon_smi
                            insert_data[mol_key] = func.mol_from_smiles(canon_smi) if canon_smi else None

                    # Реакции
                    if data.get('reaction_smiles'):
                        insert_data['reaction_mol_data'] = func.reaction_from_smiles(data['reaction_smiles'])
                    if data.get('reaction_mapped_smiles'):
                        insert_data['reaction_mol_mapped_data'] = func.reaction_from_smiles(
                            data['reaction_mapped_smiles'])

                    # Принудительно устанавливаем user_id
                    insert_data['user_id'] = current_user.id

                    # Выполняем вставку одной записи с возвратом сгенерированных ключей
                    stmt = insert(UserJournal).values(**insert_data).returning(UserJournal.id,
                                                                               UserJournal.external_id)
                    res = await db.execute(stmt)
                    new_id, new_ext_id = res.fetchone()

                    old_to_new_ext_id[old_ext_id] = new_ext_id

        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Ошибка обработки или вставки journal.tsv: {str(e)}")
        # ------------------------------------------------------------------
        # 4. ИМПОРТ АТТАЧМЕНТОВ И КОПИРОВАНИЕ ФАЙЛОВ
        # ------------------------------------------------------------------
        if "attachments.tsv" in namelist:
            try:
                with archive.open("attachments.tsv") as tsv_file:
                    text_stream = io.TextIOWrapper(tsv_file, encoding="utf-8")
                    reader = csv.DictReader(text_stream, delimiter="\t")

                    attachments_to_insert = []

                    for row in reader:
                        # Извлекаем старый external_id записи журнала
                        old_journal_ext_id = int(row.get("journal_record_ext_id"))

                        # Если этой записи журнала не оказалось в маппинге — пропускаем аттачмент
                        if old_journal_ext_id not in old_to_new_ext_id:
                            continue

                        new_journal_ext_id = old_to_new_ext_id[old_journal_ext_id]

                        # Очищаем строку от пустых значений, заменяя "" на None,
                        # чтобы СУБД корректно восприняла NULL значения
                        clean_row = {k: (v if v != "" else None) for k, v in row.items()}

                        # Обновляем внешние ключи в строке для БД
                        clean_row["user_id"] = current_user.id
                        clean_row["journal_record_ext_id"] = new_journal_ext_id

                        # --- ИСПРАВЛЕНИЕ ОШИБКИ ТИПА ДАННЫХ ДЛЯ DATE_ADDED ---
                        if clean_row.get("date_added"):
                            try:
                                # Превращаем строку '2026-06-01 23:43:51.950654' в объект datetime
                                clean_row["date_added"] = datetime.fromisoformat(clean_row["date_added"])
                            except ValueError:
                                # Если формат даты вдруг поплыл, можно засинить текущее время или dropнуть поле
                                clean_row["date_added"] = datetime.utcnow()

                        # Обновляем путь к файлу
                        old_file_path = clean_row["file_path"]
                        file_name = old_file_path.split("/")[-1]
                        new_file_path = f"{new_journal_ext_id}/{file_name}"
                        clean_row["file_path"] = new_file_path

                        # Физическое извлечение файла из архива и сохранение на диск
                        zip_file_path = f"attachments/{old_journal_ext_id}/{file_name}"

                        if zip_file_path in namelist:
                            target_dir = user_dir / str(new_journal_ext_id)
                            target_dir.mkdir(parents=True, exist_ok=True)
                            target_file_path = target_dir / file_name

                            with archive.open(zip_file_path) as source_file:
                                with open(target_file_path, "wb") as target_file:
                                    shutil.copyfileobj(source_file, target_file)
                            # TODO ДЛЯ S3:
                            # Вместо open() и shutil.copyfileobj() на локальный диск, здесь будет:
                            # file_data = archive.read(zip_file_path)
                            # await s3_client.put_object(Bucket=..., Key=f"{user_id_str}/{new_file_path}", Body=file_data)
                        # Добавляем очищенную строку в батч для вставки
                        attachments_to_insert.append(clean_row)

                    # Делаем НАСТОЯЩИЙ БАТЧ (Bulk Insert) для аттачментов
                    if attachments_to_insert:
                        # Получаем пары (external_id -> id) для этого юзера
                        j_stmt = select(UserJournal.id, UserJournal.external_id).where(
                            UserJournal.user_id == current_user.id)
                        j_res = await db.execute(j_stmt)
                        ext_to_int_id = {ext_id: int_id for int_id, ext_id in j_res.fetchall()}

                        # Проставляем правильные journal_record_id перед вставкой
                        for att_row in attachments_to_insert:
                            curr_ext = att_row["journal_record_ext_id"]
                            att_row["journal_record_id"] = ext_to_int_id[curr_ext]

                        # Массовая вставка словарей с валидными типами данных Python (datetime, int, None)
                        await db.execute(insert(JournalAttachment), attachments_to_insert)

            except Exception as e:
                await db.rollback()
                raise HTTPException(status_code=400, detail=f"Ошибка обработки аттачментов: {str(e)}")
    # Фиксируем все изменения в базе данных
    await db.commit()
    return {"status": "success", "message": "Данные успешно импортированы"}


# ------------------------------------------------------------------
# ЕНДПОИНТ 2: ПРОВЕРКА СТАТУСА И СКАЧИВАНИЕ ФАЙЛА
# ------------------------------------------------------------------
@router.get("/export-all/get")
async def check_export_status(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Проверяет статус экспорта.
    Если запись отсутствует -> 404 (Не запускался)
    Если path null -> Возвращает статус "processing" (Еще собирается)
    Если path заполнен -> Возвращает сам файл архива (FileResponse)
    """
    stmt = select(UserExport).where(UserExport.user_id == current_user.id)
    result = await db.execute(stmt)
    user_export = result.scalar_one_or_none()

    if not user_export:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Экспорт не запускался или данные устарели."
        )

    # Если путь еще пустой, значит фоновая задача еще работает
    if user_export.path is None:
        return {
            "status": "processing",
            "message": "Архив все еще формируется. Пожалуйста, подождите.",
            "started_at": user_export.created_date
        }

    # Если путь есть, формируем физический путь на диске и отдаем файл
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
    # Из БД получаем "tmp/journal_export.zip", полный путь: user_data/{user_id}/tmp/journal_export.zip
    file_path = base_user_data_path / str(current_user.id) / user_export.path

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Файл экспорта был удален на сервере. Пожалуйста, запустите экспорт заново."
        )

    return FileResponse(
        path=file_path,
        filename="journal_export.zip",
        media_type="application/zip"
    )

# ------------------------------------------------------------------
# ЕНДПОИНТ 1: ЗАПУСК ЭКСПОРТА (МГНОВЕННЫЙ ОТВЕТ)
# ------------------------------------------------------------------
@router.post("/export-all/start", status_code=status.HTTP_202_ACCEPTED)
async def start_export_user_data(
        background_tasks: BackgroundTasks,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Инициирует процесс экспорта данных в фоновом режиме.
    Сразу возвращает статус 202 Accepted. Очищает старые файлы экспорта.
    """
    user_id_str = str(current_user.id)
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
    user_tmp_dir = base_user_data_path / user_id_str / "tmp"

    # 1. Синхронно подготавливаем папки (быстрая операция)
    try:
        if user_tmp_dir.exists():
            shutil.rmtree(user_tmp_dir)
        user_tmp_dir.mkdir(parents=True, exist_ok=True)
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
    new_export = UserExport(user_id=current_user.id, path=None)
    db.add(new_export)
    await db.commit()

    # 3. Ставим тяжелую задачу архивации в бэкграунд FastAPI
    background_tasks.add_task(
        background_export_task,
        user_id=current_user.id,
        base_user_data_path=base_user_data_path,
        user_tmp_dir=user_tmp_dir,
        zip_filename=zip_filename
    )

    return {"status": "processing", "message": "Экспорт данных запущен в фоновом режиме."}

# ------------------------------------------------------------------
# ФОНОВАЯ ФУНКЦИЯ ДЛЯ ВЫПОЛНЕНИЯ ЭКСПОРТА
# ------------------------------------------------------------------
async def background_export_task(user_id: int, base_user_data_path: Path, user_tmp_dir: Path, zip_filename: str):
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
                journal_stmt = select(UserJournal).where(UserJournal.user_id == user_id)
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

                        source_file_path = base_user_data_path / str(user_id) / relative_file_path

                        if source_file_path.exists() and source_file_path.is_file():
                            shutil.copy2(source_file_path, target_file_dir / source_file_path.name)

                attachments_tsv_path = build_path / "attachments.tsv"
                with open(attachments_tsv_path, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=attach_headers, delimiter="\t")
                    writer.writeheader()
                    writer.writerows(attach_data)

                # 3. УПАКОВКА В ZIP
                archive_base = user_tmp_dir / zip_filename
                shutil.make_archive(str(archive_base), 'zip', root_dir=build_path)

            # 4. ОБНОВЛЕНИЕ СТАТУСА В БД ПОСЛЕ УСПЕШНОГО ЗАВЕРШЕНИЯ
            db_relative_path = f"tmp/{zip_filename}.zip"
            stmt = (
                update(UserExport)
                .where(UserExport.user_id == user_id)
                .values(path=db_relative_path, created_date=datetime.utcnow())
            )
            await db.execute(stmt)
            await db.commit()

        except Exception as e:
            # Тут можно логировать ошибку фонового процесса
            print(f"Ошибка фонового экспорта для пользователя {user_id}: {str(e)}")
            await db.rollback()


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

    user_id_str = str(current_user.id)
    base_user_data_path = Path(settings.USER_DATA_STORAGE_PATH).resolve()
    user_dir = base_user_data_path / user_id_str
    user_tmp_dir = user_dir / "tmp"
    user_tmp_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем загруженный ZIP файл на диск во временную папку, так как в фоне UploadFile читать нельзя
    temp_zip_path = user_tmp_dir / f"import_upload_{datetime.utcnow().timestamp()}.zip"
    try:
        with open(temp_zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось сохранить файл на сервере: {str(e)}")
    finally:
        await file.close()

    # Устанавливаем блокировку импорта
    if active_process:
        await db.execute(delete(UserExport).where(UserExport.user_id == current_user.id))

    new_lock = UserExport(user_id=current_user.id, status=ProcessStatus.PROCESSING_IMPORT, path=None)
    db.add(new_lock)
    await db.commit()

    # Запускаем фоновый импорт
    background_tasks.add_task(
        background_import_task,
        user_id=current_user.id,
        temp_zip_path=temp_zip_path,
        user_dir=user_dir,
        replace=replace
    )

    return {"status": "processing", "message": "Импорт данных успешно запущен в фоновом режиме. База заблокирована."}


async def background_import_task(
        user_id: int,
        temp_zip_path: Path,
        user_dir: Path,
        replace: bool
):
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

                # Очищаем файлы на диске
                if user_dir.exists():
                    for item in user_dir.iterdir():
                        if item.is_dir() and item.name == "tmp":
                            continue
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()

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
                        old_to_new_ext_id[old_ext_id] = new_ext_id

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

                            new_journal_ext_id = old_to_new_ext_id[old_journal_ext_id]

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

                # Если есть аттачменты — привязываем их к journal_record_id
                if attachments_to_insert:
                    j_stmt = select(UserJournal.id, UserJournal.external_id).where(UserJournal.user_id == user_id)
                    j_res = await db.execute(j_stmt)
                    ext_to_int_id = {ext_id: int_id for int_id, ext_id in j_res.fetchall()}

                    db_attachments = []
                    for att_row, old_ext, new_ext, f_name in attachments_to_insert:
                        att_row["journal_record_id"] = ext_to_int_id[new_ext]
                        db_attachments.append(att_row)

                    await db.execute(insert(JournalAttachment), db_attachments)

                await db.commit()

            # Шаг 3: Физическое копирование файлов на диск
            if attachments_to_insert:
                for att_row, old_ext, new_ext, f_name in attachments_to_insert:
                    zip_file_path = f"attachments/{old_ext}/{f_name}"
                    if zip_file_path in namelist:
                        target_dir = user_dir / str(new_ext)
                        target_dir.mkdir(parents=True, exist_ok=True)
                        with archive.open(zip_file_path) as source_file:
                            with open(target_dir / f_name, "wb") as target_file:
                                shutil.copyfileobj(source_file, target_file)

            # Снимаем блокировку импорта
            async with users_session_factory() as db:
                await db.execute(delete(UserExport).where(UserExport.user_id == user_id))
                await db.commit()

    except Exception as e:
        # Если упали — пишем статус FAILED
        async with users_session_factory() as db:
            stmt = (
                update(UserExport)
                .where(UserExport.user_id == user_id)
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