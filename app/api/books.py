from fastapi import APIRouter, Depends, Query
from typing import List
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.settings import settings
from app.core.db import get_archive_db

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search/ids")
async def search_book_ids(
        smiles: str,
        exact: bool = False,
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Поиск ID в книжной базе.
    exact=True -> точное совпадение структур.
    exact=False -> поиск подструктуры.
    """
    operator = "@=" if exact else "@>"

    # Используем тройное двоеточие ::: для экранирования типа MOL в SQLAlchemy
    query = sa.text(f"""
        SELECT id FROM book_base
        WHERE mol_data {operator} cast(:smiles as mol)
        AND is_deleted = false
        LIMIT :limit
    """)

    result = await db.execute(query, {
        "smiles": smiles,
        "limit": settings.SEARCH_LIMIT
    })

    ids = [row[0] for row in result.fetchall()]
    return {"ids": ids, "count": len(ids)}


@router.get("/search/by-ids")
async def get_books_by_ids(
        ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Получение полных данных по списку ID из книжной базы.
    """
    if not ids:
        return []

    query = sa.text("""
                    SELECT id,
                           external_id,
                           name,
                           book_name,
                           pages,
                           smiles,
                           "references",
                           date_added
                    FROM book_base
                    WHERE id = ANY (:ids)
                      AND is_deleted = false
                    """)

    result = await db.execute(query, {"ids": ids})

    books = []
    for row in result.fetchall():
        books.append({
            "id": row[0],
            "external_id": row[1],
            "name": row[2],
            "book_name": row[3],
            "pages": row[4],
            "smiles": row[5],
            "references": row[6],
            "date_added": row[7]
        })

    return books