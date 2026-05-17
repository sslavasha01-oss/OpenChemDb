from typing import List

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from rdkit import Chem
from rdkit.Chem import rdChemReactions, Draw, AllChem
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_archive_db  # Твой генератор сессий для archive_db
from app.core.settings import settings
from fastapi import HTTPException
import re

ATOM_MAPPING_REGEX = re.compile(r"\[[^\]]+:\d+\]")

router = APIRouter(prefix="/reactions", tags=["reactions"])


@router.get("/search/ids/smiles")
async def search_reaction_ids_smiles(
        smiles: str,
        exact: bool = False,
        db: AsyncSession = Depends(get_archive_db)
):
    # 1. Сначала чистим ввод
    clean_smiles = canonicalize_reaction_smiles(smiles)

    # Определяем колонку
    use_mapped = bool(ATOM_MAPPING_REGEX.search(smiles))
    reaction_column = "reaction_mapped_data" if use_mapped else "reaction_raw_data"

    if not exact:
        where_clause = f"{reaction_column} @> :smiles\\:\\:reaction"
        params = {"smiles": clean_smiles, "limit": settings.SEARCH_LIMIT}
    else:
        # Режим Exact Match
        parts = clean_smiles.split('>>')  # Используем уже канонизированный clean_smiles
        r_part = parts[0].strip() if len(parts) > 0 and parts[0].strip() else None
        p_part = parts[-1].strip() if len(parts) > 1 and parts[-1].strip() else None

        conditions = []
        params = {"limit": settings.SEARCH_LIMIT}

        def get_components(smiles_str):
            if not smiles_str: return None
            # Здесь фрагменты уже фактически каноничны после canonicalize_smiles,
            # но split по точке всё равно нужен для GIN индекса
            return [s.strip() for s in smiles_str.split('.') if s.strip()]

        if r_part:
            params["r_components"] = get_components(r_part)
            conditions.append(f"""
                (string_to_array(split_part(reaction_to_smiles(reaction_raw_data)\\:\\:text, '>', 1), '.') @> 
                 :r_components\\:\\:text[])
            """)

        if p_part:
            params["p_components"] = get_components(p_part)
            conditions.append(f"""
                (string_to_array(split_part(reaction_to_smiles(reaction_raw_data)\\:\\:text, '>', 3), '.') @> 
                 :p_components\\:\\:text[])
            """)

        where_clause = " AND ".join(conditions) if conditions else "is_deleted = false"

    await db.execute(sa.text("SET LOCAL statement_timeout = 3000;"))

    query = sa.text(f"""
            SELECT id FROM archive_reactions
            WHERE {where_clause}
            AND is_deleted = false
        LIMIT :limit
    """)

    try:
        result = await db.execute(query, params)
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        print(f"DB Search Error (SMILES): {e}")
        raise HTTPException(status_code=500, detail="Database error")


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
    use_mapped = bool(ATOM_MAPPING_REGEX.search(smiles))
    column_name = "reaction_mapped_data" if use_mapped else "reaction_raw_data"
    print(use_mapped)
    await db.execute(sa.text("SET LOCAL statement_timeout = 3000;"))

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
        raise HTTPException(status_code=500, detail="Database error")


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


from xml.etree.ElementTree import fromstring as xml_fromstring


def crop_svg_borders(svg_text: str, padding: int = 15) -> str:
    """
    Парсит SVG, находит точные физические границы (Bounding Box) всех
    отрисованных элементов и переписывает viewBox ровно под них.
    """
    try:
        # Находим исходные размеры холста
        size_match = re.search(r'width="(\d+)px"\s+height="(\d+)px"', svg_text)
        if not size_match:
            return svg_text

        init_w = int(size_match.group(1))
        init_h = int(size_match.group(2))

        # Вырезаем пространство имен, чтобы ElementTree не падал
        svg_no_ns = re.sub(r' xmlns="[^"]+"', '', svg_text, count=1)
        root = xml_fromstring(svg_no_ns)

        min_x, min_y = float('inf'), float('inf')
        max_x, max_y = float('-inf'), float('-inf')

        # Сканируем координаты всех элементов (пути, текст, фигуры)
        for elem in root.iter():
            if elem.tag == 'svg' or (
                    elem.tag == 'rect' and elem.get('style') and 'fill:#FFFFFF' in elem.get('style') and elem.get(
                    'x') == '0'):
                continue

            xs, ys = [], []

            if elem.tag in ('rect', 'text'):
                if elem.get('x'): xs.append(float(elem.get('x')))
                if elem.get('y'): ys.append(float(elem.get('y')))
            elif elem.tag == 'circle':
                if elem.get('cx'): xs.append(float(elem.get('cx')))
                if elem.get('cy'): ys.append(float(elem.get('cy')))
            elif elem.tag == 'path':
                d = elem.get('d', '')
                coords = [float(x) for x in re.findall(r'[-+]?\d*\.\d+|\d+', d)]
                xs.extend(coords[0::2])
                ys.extend(coords[1::2])

            if xs:
                min_x = min(min_x, min(xs))
                max_x = max(max_x, max(xs))
            if ys:
                min_y = min(min_y, min(ys))
                max_y = max(max_y, max(ys))

        # Если контент пустой, просто делаем SVG адаптивным
        if min_x == float('inf') or min_y == float('inf'):
            return svg_text.replace(f'width="{init_w}px" height="{init_h}px"',
                                    f'viewBox="0 0 {init_w} {init_h}" width="100%" height="auto"')

        # Формируем viewBox строго по границам контента + пэддинг
        crop_x = max(0, min_x - padding)
        crop_y = max(0, min_y - padding)
        crop_w = min(init_w, (max_x - min_x) + padding * 2)
        crop_h = min(init_h, (max_y - min_y) + padding * 2)

        # Заменяем фиксированные px на адаптивный viewBox
        svg_cropped = svg_text.replace(
            f'width="{init_w}px" height="{init_h}px"',
            f'viewBox="{crop_x:.1f} {crop_y:.1f} {crop_w:.1f} {crop_h:.1f}" width="100%" height="auto"'
        )
        return svg_cropped

    except Exception as e:
        print(f"Error inside crop_svg_borders: {e}")
        return svg_text


def generate_reaction_svg(smiles: str) -> str:
    if not smiles:
        return ""

    try:
        rxn = rdChemReactions.ReactionFromSmarts(smiles, useSmiles=True)

        if rxn:
            # 1. Генерируем 2D-координаты для абсолютно всех участников
            for i in range(rxn.GetNumReactantTemplates()):
                mol = rxn.GetReactantTemplate(i)
                mol.RemoveAllConformers()
                AllChem.Compute2DCoords(mol)

            for i in range(rxn.GetNumProductTemplates()):
                mol = rxn.GetProductTemplate(i)
                mol.RemoveAllConformers()
                AllChem.Compute2DCoords(mol)

            for i in range(rxn.GetNumAgentTemplates()):
                mol = rxn.GetAgentTemplate(i)
                mol.RemoveAllConformers()
                AllChem.Compute2DCoords(mol)

            # 2. РЕНДЕРИНГ: Используем стабильный большой холст.
            # RDKit отрисует даже гигантские схемы с высокой четкостью и без каши,
            # а избыток белого пространства гарантированно срежет функция кропа.
            master_w, master_h = 2400, 700

            d2d = Draw.MolDraw2DSVG(master_w, master_h)
            opts = d2d.drawOptions()
            opts.fixedFontSize = 14
            opts.annotationFontScale = 0.8
            opts.padding = 0.02

            d2d.DrawReaction(rxn)
            d2d.FinishDrawing()

            raw_svg = d2d.GetDrawingText()

            # Обрезаем все пустые поля под ноль
            return crop_svg_borders(raw_svg, padding=15)

        # Fallback для одной молекулы
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            mol.RemoveAllConformers()
            AllChem.Compute2DCoords(mol)

            master_w, master_h = 600, 500
            d2d = Draw.MolDraw2DSVG(master_w, master_h)
            d2d.drawOptions().padding = 0.02
            d2d.DrawMolecule(mol)
            d2d.FinishDrawing()

            raw_svg = d2d.GetDrawingText()
            return crop_svg_borders(raw_svg, padding=12)

    except Exception as e:
        print(f"RDKit Render Error for {smiles[:20]}: {e}")

    return ""


def canonicalize_reaction_smiles(smi: str):
    if not smi:
        return None

    # Вспомогательная функция для канонизации отдельного блока (реагентов или продуктов)
    def canonicalize_side(side_str: str) -> str:
        if not side_str.strip():
            return ""

        canonical_mols = []
        # Разделяем компоненты (например, если несколько молекул через точку)
        parts = side_str.split('.')

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # MolFromSmiles из коробки идеально парсит И Кекуле, И ароматику,
            # автоматически приводя всё к единому ароматическому виду.
            mol = Chem.MolFromSmiles(part)
            if mol:
                # Генерируем каноничный SMILES для этой конкретной молекулы
                canonical_mols.append(Chem.MolToSmiles(mol))
            else:
                # Если вдруг RDKit не смог распарсить, оставляем как было
                canonical_mols.append(part)

        # Сортируем компоненты, чтобы порядок молекул (A.B и B.A) тоже был каноничным
        canonical_mols.sort()
        return ".".join(canonical_mols)

    # Разделяем саму реакцию на реагенты, агенты и продукты
    # SMILES реакции может содержать один или два знака '>' (разделители)
    if ">>" in smi:
        left, right = smi.split(">>", 1)
        # Проверяем, нет ли там еще агентов (трехкомпонентный SMILES: R>A>P)
        if ">" in left:
            reactants, agents = left.split(">", 1)
            return f"{canonicalize_side(reactants)}>{canonicalize_side(agents)}>{canonicalize_side(right)}"
        else:
            return f"{canonicalize_side(left)}>>{canonicalize_side(right)}"
    elif ">" in smi:
        # На случай если пришел формат R>A>P, но без двойного знака
        parts = smi.split(">")
        if len(parts) == 3:
            return f"{canonicalize_side(parts[0])}>{canonicalize_side(parts[1])}>{canonicalize_side(parts[2])}"
        elif len(parts) == 2:
            return f"{canonicalize_side(parts[0])}>>{canonicalize_side(parts[1])}"

    # Если это вообще не реакция, а просто набор молекул
    return canonicalize_side(smi)
