from typing import List

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from rdkit import Chem
from rdkit.Chem import rdChemReactions, Draw
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_archive_db  # Твой генератор сессий для archive_db
from app.core.settings import settings

router = APIRouter(prefix="/reactions", tags=["reactions"])


@router.get("/search/ids/smiles")
async def search_reaction_ids_smiles(
        smiles: str,
        exact: bool = False,
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Поиск ID реакций.
    Если в smiles есть маппинг (символ ':'), ищем по mapped_data, иначе по raw_data.
    """
    use_mapped = ":" in smiles
    column_name = "reaction_mapped_data" if use_mapped else "reaction_raw_data"

    operator = "@>"

    query = sa.text(f"""
            SELECT id FROM archive_reactions
            WHERE {column_name} {operator} cast(:smiles as reaction)
            AND is_deleted = false
            ORDER BY id DESC
            LIMIT :limit
        """)

    try:
        result = await db.execute(query, {
            "smiles": smiles,
            "limit": settings.SEARCH_LIMIT
        })
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        print(f"DB Search Error (SMILES): {e}")
        return {"ids": [], "count": 0, "error": str(e)}

@router.get("/search/ids/smarts")
async def search_reaction_ids_smarts(
        smiles: str,
        db: AsyncSession = Depends(get_archive_db)
):
    """
    Поиск ID реакций.
    Если в smiles есть маппинг (символ ':'), ищем по mapped_data, иначе по raw_data.
    """
    # Определяем, есть ли маппинг в запросе
    use_mapped = ":" in smiles
    column_name = "reaction_mapped_data" if use_mapped else "reaction_raw_data"

    processed_query = smiles
    # Выбираем оператор
    operator = "@>"

    # 3. SQL ЗАПРОС
    # Используем reaction_from_smarts — он переварит и SMILES, и SMARTS
    query = sa.text(f"""
            SELECT id FROM archive_reactions
            WHERE {column_name} {operator} reaction_from_smarts(:smiles)
            AND is_deleted = false
            LIMIT :limit
        """)

    try:
        result = await db.execute(query, {
            "smiles": processed_query,
            "limit": settings.SEARCH_LIMIT
        })
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        # Если бд все же ругается на синтаксис SMARTS
        print(f"DB Search Error: {e}")
        return {"ids": [], "count": 0, "error": str(e)}


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
        raw_smiles = row[3]
        reactions.append({
            "id": row[0],
            "external_id": row[1],
            "doi": row[2],
            "reaction_raw_smiles": raw_smiles,
            "reaction_mapped_smiles": row[4],
            "references": row[5],
            "conditions": row[6],
            "yield_text": row[7],
            "procedure": row[8],
            "svg_content": generate_reaction_svg(raw_smiles),
        })

    return reactions


def generate_reaction_svg(smiles: str) -> str:
    if not smiles:
        return ""

    try:
        # 1. Сначала пробуем распарсить как реакцию через Smarts (это надежнее)
        rxn = rdChemReactions.ReactionFromSmarts(smiles, useSmiles=True)

        if rxn:
            # Даем RDKit достаточно места, но CSS потом сожмет его до 50%
            d2d = Draw.MolDraw2DSVG(800, 300)

            opts = d2d.drawOptions()
            opts.prepareMolsBeforeDrawing = True  # Магическая кнопка для чистки координат
            opts.fixedFontSize = 14

            d2d.DrawReaction(rxn)
            d2d.FinishDrawing()

            svg = d2d.GetDrawingText()
            # Важный хак: делаем SVG адаптивным, убирая фиксированные width/height из тега
            return svg.replace('width="800px"', 'width="100%"').replace('height="300px"', 'height="auto"')

        # 2. Fallback: если это не реакция, а просто молекула
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            d2d = Draw.MolDraw2DSVG(400, 200)
            d2d.DrawMolecule(mol)
            d2d.FinishDrawing()
            svg = d2d.GetDrawingText()
            return svg.replace('width="400px"', 'width="100%"').replace('height="200px"', 'height="auto"')

    except Exception as e:
        # Если RDKit совсем упал, в логах будет видно почему
        print(f"RDKit Render Error for {smiles[:20]}: {e}")

    return ""
