from fastapi import APIRouter, Depends, HTTPException, status
from rdkit import Chem
from rdkit.Chem import Draw
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, func, update, select, desc, delete
from typing import Dict, List

from app.models.user_journal import UserJournal
from app.models.user import User
from app.schemas.user_journal import UserJournalSchema
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
    data = record_data.model_dump(exclude={'id', 'external_id', 'date_added', 'date_modified', 'product_svg'})

    # Подготавливаем словарь для вставки
    # Нам нужно подменить значения для всех колонок *_mol_data на SQL-функции RDKit
    insert_data = {}

    for key, value in data.items():
        # Сначала просто копируем значение
        insert_data[key] = value

        # А теперь, ЕСЛИ это поле с mol_data, пробуем сгенерировать его из SMILES
        if key.endswith('_mol_data'):
            smiles_key = key.replace('_mol_data', '_smiles')
            smiles_value = data.get(smiles_key)
            if smiles_value:
                insert_data[key] = func.mol_from_smiles(smiles_value)

        # Логика для реакций
        elif key == 'reaction_mol_data' and data.get('reaction_smiles'):
            insert_data[key] = func.reaction_from_smiles(data['reaction_smiles'])

        elif key == 'reaction_mol_mapped_data' and data.get('reaction_mapped_smiles'):
            insert_data[key] = func.reaction_from_smiles(data['reaction_mapped_smiles'])

    # Принудительно устанавливаем user_id из авторизации
    insert_data['user_id'] = current_user.id
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


@router.delete("/delete/{external_id}", status_code=status.HTTP_200_OK)
async def delete_journal_record(
        external_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    try:
        stmt = (
            delete(UserJournal.__table__)
            .where(
                UserJournal.user_id == current_user.id,
                UserJournal.external_id == external_id
            )
            .returning(UserJournal.id) # Возвращаем id для подтверждения удаления
        )

        result = await db.execute(stmt)
        deleted_id = result.scalar_one_or_none()

        if not deleted_id:
            raise HTTPException(status_code=404, detail="Record not found")

        await db.commit()
        return {"status": "success", "message": f"Record #{external_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


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

        return output

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