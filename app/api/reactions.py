from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.settings import settings
from app.core.db import get_archive_db  # Твой генератор сессий для archive_db
from app.utils.utils import canonicalize_smiles

router = APIRouter(prefix="/reactions", tags=["reactions"])


@router.get("/search/ids")
async def search_reaction_ids(
        smiles: str,
        exact: bool = False,
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Поиск ID реакций.
    Если в smiles есть маппинг (символ ':'), ищем по mapped_data, иначе по raw_data.
    """
    # Определяем, есть ли маппинг в запросе
    use_mapped = ":" in smiles
    column_name = "reaction_mapped_data" if use_mapped else "reaction_raw_data"

    canonical_smiles = canonicalize_smiles(smiles)

    # Выбираем оператор: = для точного, @> для подструктуры
    operator = "@=" if exact else "@>"

    # Формируем SQL запрос
    # Используем текстовый запрос, так как операторы RDKit специфичны
    query = sa.text(f"""
        SELECT id FROM archive_reactions
        WHERE {column_name} {operator} cast(:smiles as reaction)
        AND is_deleted = false
        LIMIT :limit
    """)

    result = await db.execute(query, {"smiles": canonical_smiles, "limit": settings.SEARCH_LIMIT})
    ids = [row[0] for row in result.fetchall()]

    return {"ids": ids, "count": len(ids)}


@router.get("/search/by-ids")
async def get_reactions_by_ids(
        ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Получение полных данных по списку ID.
    """
    if not ids:
        return []

    query = sa.text("""
                    SELECT id,
                           external_id,
                           doi,
                           reaction_raw_smiles,
                           reaction_mapped_smiles,
                           "references",
                           conditions,
                           yield_text, procedure
                    FROM archive_reactions
                    WHERE id = ANY (:ids)
                      AND is_deleted = false
                    """)

    result = await db.execute(query, {"ids": ids})

    # Формируем список словарей для ответа
    reactions = []
    for row in result.fetchall():
        reactions.append({
            "id": row[0],
            "external_id": row[1],
            "doi": row[2],
            "reaction_raw_smiles": row[3],
            "reaction_mapped_smiles": row[4],
            "references": row[5],
            "conditions": row[6],
            "yield_text": row[7],
            "procedure": row[8]
        })

    return reactions