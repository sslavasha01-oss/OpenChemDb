from fastapi import APIRouter, Depends, HTTPException
from rdkit import Chem
from rdkit.Chem import Draw
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, func, update, select, desc
from typing import Dict, List

from app.models import UserJournal
from app.models.user import User
from app.schemas.UserJournal import UserJournalSchema
from app.core.db import get_users_db
from app.api.deps import get_current_user

router = APIRouter(prefix="/my-journal", tags=["Journal"])


@router.post("/add", response_model=UserJournalSchema)
async def add_journal_record(
        record_data: UserJournalSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    # Превращаем Pydantic модель в словарь, исключая служебные поля и пустые mol_data
    data = record_data.model_dump(exclude={'id', 'external_id', 'date_added', 'date_modified'})

    # Принудительно устанавливаем user_id из авторизации
    data['user_id'] = current_user.id

    # Подготавливаем словарь для вставки
    # Нам нужно подменить значения для всех колонок *_mol_data на SQL-функции RDKit
    insert_data = {}

    for key, value in data.items():
        if value is None:
            insert_data[key] = None
            continue

        # Обработка молекул (продукт и реагенты)
        if key.endswith('_mol_data'):
            smiles_key = key.replace('_mol_data', '_smiles')
            smiles_value = data.get(smiles_key)
            if smiles_value:
                # В Postgres расширение RDKit предоставляет функцию mol_from_smiles
                insert_data[key] = func.mol_from_smiles(smiles_value)

        # Обработка реакций
        elif key.endswith('_mol_data') or key.endswith('_mapped_data'):
            # Важно: в миграции у тебя reaction_mol_data и reaction_mol_mapped_data
            # Ищем соответствующие smiles поля
            suffix = '_smiles' if key.endswith('_data') else '_mapped_smiles'
            smiles_key = key.replace('_mol_data', '_smiles').replace('_mol_mapped_data', '_mapped_smiles')

            smiles_value = data.get(smiles_key)
            if smiles_value:
                # В Postgres функция называется reaction_from_smiles
                insert_data[key] = func.reaction_from_smiles(smiles_value)

    # Выполняем вставку с возвратом всей строки (RETURNING *)
    # Триггер в базе сам выставит external_id
    try:
        stmt = (
            insert(UserJournal)
            .values(**insert_data)
            .returning(UserJournal)
        )

        result = await db.execute(stmt)
        await db.commit()

        new_record = result.scalar_one()
        return new_record

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.put("/update/{external_id}", response_model=UserJournalSchema)
async def update_journal_record(
        external_id: int,
        record_data: UserJournalSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    # Извлекаем данные, исключая системные поля и те, что не должны меняться
    # Мы исключаем user_id и external_id из данных для обновления,
    # так как они используются только в WHERE
    data = record_data.model_dump(
        exclude={'id', 'user_id', 'external_id', 'date_added', 'date_modified'},
        exclude_unset=True  # Обновляем только те поля, которые прислал фронт
    )

    if not data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    update_values = {}

    for key, value in data.items():
        # Обычная обработка None
        if value is None:
            update_values[key] = None
            continue

        # Логика для молекул (продукты и реагенты)
        if key.endswith('_mol_data'):
            smiles_key = key.replace('_mol_data', '_smiles')
            # Берем SMILES либо из пришедших данных, либо (если не прислали)
            # придется оставить как есть, но обычно фронт шлет пару.
            smiles_value = data.get(smiles_key)
            if smiles_value:
                update_values[key] = func.mol_from_smiles(smiles_value)

        # Логика для реакций
        elif key.endswith('_mol_mapped_data') or (key == 'reaction_mol_data'):
            # Определяем ключ со SMILES для конкретного поля
            if key == 'reaction_mol_data':
                smiles_key = 'reaction_smiles'
            else:
                smiles_key = 'reaction_mapped_smiles'

            smiles_value = data.get(smiles_key)
            if smiles_value:
                update_values[key] = func.reaction_from_smiles(smiles_value)

        else:
            # Все остальные поля (Decimal, Text и т.д.)
            update_values[key] = value

    try:
        # Формируем запрос
        stmt = (
            update(UserJournal.__table__)
            .where(
                UserJournal.user_id == current_user.id,
                UserJournal.external_id == external_id
            )
            .values(**update_values)
            .returning(UserJournal.__table__)
        )

        result = await db.execute(stmt)
        updated_row = result.mappings().first()

        if not updated_row:
            raise HTTPException(status_code=404, detail="Record not found")

        await db.commit()
        return updated_row

    except Exception as e:
        await db.rollback()
        # В продакшене лучше логировать e, а пользователю отдавать generic error
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@router.get("/list", response_model=List[UserJournalSchema])
async def get_journal_list(
        limit: int = 20,
        offset: int = 0,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Возвращает список записей журнала текущего пользователя.
    Сортировка: от новых к старым (external_id DESC).
    """
    try:
        # Формируем запрос
        stmt = (
            select(UserJournal)
            .where(UserJournal.user_id == current_user.id)
            .order_by(desc(UserJournal.external_id))  # Последние записи первыми
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)

        # Используем scalars(), так как запрашиваем целиком модель UserJournal
        records = result.scalars().all()

        output = []
        for rec in records:
            schema_rec = UserJournalSchema.model_validate(rec)
            if schema_rec.product_smiles:
                schema_rec.product_svg = generate_molecule_svg(schema_rec.product_smiles)
            output.append(schema_rec)

        return records

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch list: {str(e)}")


@router.get("/count")
async def get_journal_count(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Возвращает общее количество записей в журнале текущего пользователя.
    """
    try:
        # Считаем записи только для конкретного пользователя
        stmt = (
            select(func.count())
            .select_from(UserJournal)
            .where(UserJournal.user_id == current_user.id)
        )

        result = await db.execute(stmt)
        total_count = result.scalar()

        return {"total": total_count}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error counting records: {str(e)}")



def generate_molecule_svg(smiles: str) -> str:
    """
    Генерация SVG для одиночной молекулы.
    """
    if not smiles:
        return ""

    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            # Для одиночной молекулы 400x200 обычно достаточно
            d2d = Draw.MolDraw2DSVG(400, 200)

            opts = d2d.drawOptions()
            opts.prepareMolsBeforeDrawing = True
            opts.fixedFontSize = 14

            d2d.DrawMolecule(mol)
            d2d.FinishDrawing()

            svg = d2d.GetDrawingText()
            # Делаем SVG адаптивным для фронтенда
            return svg.replace('width="400px"', 'width="100%"').replace('height="200px"', 'height="auto"')

    except Exception as e:
        print(f"RDKit Render Error (Molecule) for {smiles[:20]}: {e}")

    return ""