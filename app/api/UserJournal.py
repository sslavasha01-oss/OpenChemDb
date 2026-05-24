from fastapi import APIRouter, Depends, HTTPException, status, Query
from rdkit import Chem
from rdkit.Chem import Draw
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, func, update, select, desc, delete
from typing import Dict, List, Optional
import sqlalchemy as sa

from app.core.settings import settings
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
    data = record_data.model_dump(
        exclude={'id', 'external_id', 'date_added', 'date_modified', 'product_svg'},
        exclude_none=True
    )

    insert_data = {}
    for key, value in data.items():
        # Если это служебные поля mol_data, которые фронтенд прислал пустыми — игнорируем их
        if key.endswith('_mol_data') or key in ('reaction_mol_data', 'reaction_mol_mapped_data'):
            continue

        insert_data[key] = value

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
        insert_data['reaction_mol_mapped_data'] = func.reaction_from_smiles(data['reaction_mapped_smiles'])

    # Принудительно устанавливаем user_id
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
    # 1. Извлекаем только те поля, которые фронтенд явно передал в запросе
    data = record_data.model_dump(
        exclude={'id', 'user_id', 'external_id', 'date_added', 'date_modified', 'product_svg'},
        exclude_unset=True  # Обновляем только присланные поля
    )

    if not data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    # 2. Переносим во flat-словарь все стандартные поля (числа, текст и т.д.)
    # При этом полностью игнорируем сырые *_mol_data из Pydantic
    update_values = {}
    for key, value in data.items():
        if key.endswith('_mol_data') or key in ('reaction_mol_data', 'reaction_mol_mapped_data'):
            continue
        update_values[key] = value

    # 3. Канонизируем пришедшие SMILES и обновляем RDKit-поля

    # Продукт
    if 'product_smiles' in data:
        canon_smi = canonicalize_molecule_smiles(data['product_smiles'])
        update_values['product_smiles'] = canon_smi
        update_values['product_mol_data'] = func.mol_from_smiles(canon_smi) if canon_smi else None

    # Реагенты 1-5
    for i in range(1, 6):
        smiles_key = f'reagent{i}_smiles'
        mol_key = f'reagent{i}_mol_data'
        if smiles_key in data:
            canon_smi = canonicalize_molecule_smiles(data[smiles_key])
            update_values[smiles_key] = canon_smi
            update_values[mol_key] = func.mol_from_smiles(canon_smi) if canon_smi else None

    # Реакции
    if 'reaction_smiles' in data:
        rxn_smiles = data['reaction_smiles']
        update_values['reaction_mol_data'] = func.reaction_from_smiles(rxn_smiles) if rxn_smiles else None

    if 'reaction_mapped_smiles' in data:
        rxn_m_smiles = data['reaction_mapped_smiles']
        update_values['reaction_mol_mapped_data'] = func.reaction_from_smiles(rxn_m_smiles) if rxn_m_smiles else None

    try:
        # Формируем SQL-запрос обновления
        stmt = (
            update(UserJournal)
            .where(
                UserJournal.user_id == current_user.id,
                UserJournal.external_id == external_id
            )
            .values(**update_values)
            .returning(UserJournal)  # Возвращаем ORM-объект целиком
        )

        result = await db.execute(stmt)

        # Используем scalar_one_or_none(), так как запись по external_id может не найтись
        updated_record = result.scalar_one_or_none()

        if not updated_record:
            await db.rollback()
            raise HTTPException(status_code=404, detail="Record not found or access denied")

        await db.commit()

        # Возвращаем чистый ORM-объект, FastAPI сам провалидирует его через UserJournalSchema
        return updated_record

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"UPDATE ERROR (External ID {external_id}): {e}")
        raise HTTPException(status_code=500, detail="Database error during update")


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


@router.get("/search/ids")
async def search_journal_ids(
        product_smiles: Optional[str] = None,
        reagent_smiles: Optional[str] = None,
        exact: bool = False,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Поиск ID записей журнала по подструктуре продукта и/или любого из 5 реагентов.
    Возвращает список ID, отсортированных по external_id в возрастающем порядке.
    """
    if not product_smiles and not reagent_smiles:
        raise HTTPException(status_code=400, detail="At least one search structure must be provided")

    # Базовые условия, общие для любого сценария
    where_clauses = ["user_id = :user_id"]
    params = {
        "user_id": current_user.id,
        "limit": settings.SEARCH_LIMIT
    }

    # Если передан продукт
    if product_smiles:
        clean_product = canonicalize_molecule_smiles(product_smiles)
        where_clauses.append("product_mol_data @> :product_smiles\\:\\:mol")
        params["product_smiles"] = clean_product

    # Если передан реагент (проверяем все 5 колонок через OR)
    if reagent_smiles:
        clean_reagent = canonicalize_molecule_smiles(reagent_smiles)
        reagent_clause = """(
            reagent1_mol_data @> :reagent_smiles\\:\\:mol OR
            reagent2_mol_data @> :reagent_smiles\\:\\:mol OR
            reagent3_mol_data @> :reagent_smiles\\:\\:mol OR
            reagent4_mol_data @> :reagent_smiles\\:\\:mol OR
            reagent5_mol_data @> :reagent_smiles\\:\\:mol
        )"""
        where_clauses.append(reagent_clause)
        params["reagent_smiles"] = clean_reagent

    # Собираем финальный SQL-запрос
    query_string = f"""
        SELECT id FROM user_journal
        WHERE {" AND ".join(where_clauses)}
        ORDER BY external_id ASC
        LIMIT :limit
    """

    query = sa.text(query_string)
    print(query_string)

    try:
        result = await db.execute(query, params)
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        print(f"DB Search Error (Journal Substructure): {e}")
        raise HTTPException(status_code=500, detail="Database error during structure search")


@router.get("/search/by-ids", response_model=List[UserJournalSchema])
async def get_journal_by_ids(
        ids: List[int] = Query(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_users_db)
):
    """
    Получение полных данных журнала по списку ID с проверкой прав доступа текущего пользователя.
    """
    if not ids:
        return []

    # Строим безопасный запрос, исключающий доступ к чужим записям
    query = sa.text("""
        SELECT * FROM user_journal
        WHERE id = ANY (:ids)
          AND user_id = :user_id
        ORDER BY external_id ASC
    """)

    try:
        result = await db.execute(query, {"ids": ids, "user_id": current_user.id})
        # .mappings() позволяет обращаться к полям по именам (как в словаре)
        rows = result.mappings().all()

        output = []
        for row in rows:
            # Превращаем RowMapping в обычный словарь для Pydantic
            row_dict = dict(row)

            # Валидируем через вашу Pydantic-схему
            schema_rec = UserJournalSchema.model_validate(row_dict)

            # Добавляем SVG-графику для продукта, если есть SMILES
            if schema_rec.product_smiles:
                schema_rec.product_svg = generate_molecule_svg(schema_rec.product_smiles)

            output.append(schema_rec)

        return output

    except Exception as e:
        print(f"Error fetching journal records by IDs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch journal records")


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

def canonicalize_molecule_smiles(smi: str):
    if not smi:
        return None
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol:
            Chem.SanitizeMol(mol)
            return Chem.MolToSmiles(mol)
    except:
        pass
    return smi