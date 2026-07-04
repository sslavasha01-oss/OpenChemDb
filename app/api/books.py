from fastapi import APIRouter, Depends, Query
from typing import List
import sqlalchemy as sa
from rdkit import Chem
from rdkit.Chem import Draw
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.settings import settings
from app.core.db import get_archive_db
from fastapi import HTTPException

router = APIRouter(prefix="/books", tags=["books"])


@router.get("/search/ids")
async def search_book_ids(
        smiles: str,
        exact: bool = False,
        db: AsyncSession = Depends(get_archive_db)
):
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
        return None

    clean_smiles = canonicalize_molecule_smiles(smiles)

    if not clean_smiles:
        raise HTTPException(status_code=400, detail=f"Invalid Molecule SMILES: {smiles}")

    if not exact:
        # Для подструктурного поиска оставляем работу с типом mol
        where_clause = "mol_data @> :smiles\\:\\:mol"
        params = {"smiles": clean_smiles, "limit": settings.SEARCH_LIMIT}
    else:
        # Режим Exact Match через массивы каноничных SMILES (аналог логики из реакций)
        # Разбиваем на фрагменты (соли, смеси), если они есть
        components = [s.strip() for s in clean_smiles.split('.') if s.strip()]

        # Используем встроенную функцию rdkit (mol_to_smiles) или хранимый текст.
        # В примере ниже предполагается, что мы сравниваем каноничный массив
        where_clause = """
            (string_to_array(smiles, '.') @> :components\\:\\:text[])
        """
        params = {
            "components": components,
            "limit": settings.SEARCH_LIMIT
        }

    query = sa.text(f"""
        SELECT id FROM book_base
        WHERE {where_clause}
        AND is_deleted = false
        LIMIT :limit
    """)

    try:
        result = await db.execute(query, params)
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        print(f"DB Search Error (Books Exact): {e}")
        raise HTTPException(status_code=500, detail="Database error")

@router.get("/search/ids/smarts")
async def search_book_ids_smarts(
    smarts: str,
    db: AsyncSession = Depends(get_archive_db)
):
    """
    Поиск ID молекул в книжной базе по SMARTS паттерну.
    """
    mol_pat = Chem.MolFromSmarts(smarts)
    if not mol_pat:
        raise HTTPException(status_code=400, detail=f"Invalid Molecule SMARTS: {smarts}")
    # Используем mol_from_smarts, так как он корректно интерпретирует
    # специфические для SMARTS запросы (дикие карты, количество связей и т.д.)
    query = sa.text("""
            SELECT id FROM book_base
            WHERE mol_data @> cast(:smarts as qmol)
            AND is_deleted = false
            LIMIT :limit
    """)

    try:
        result = await db.execute(query, {
            "smarts": smarts,
            "limit": settings.SEARCH_LIMIT
        })
        ids = [row[0] for row in result.fetchall()]
        return {"ids": ids, "count": len(ids)}
    except Exception as e:
        # Часто возникает, если SMARTS синтаксически некорректен
        print(f"DB Search Error (SMARTS): {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/search/by-ids")
async def get_books_by_ids(
        ids: List[int] = Query(...),
        db: AsyncSession = Depends(get_archive_db)
):
    if not ids:
        return []

    # ТЯНЕМ НАПРЯМУЮ ТЕКСТОВОЕ ПОЛЕ mol_file_raw
    query = sa.text("""
                    SELECT id,
                           external_id,
                           name,
                           book_name,
                           pages,
                           smiles,
                           "references",
                           date_added,
                           mol_file_raw
                    FROM book_base
                    WHERE id = ANY (:ids)
                      AND is_deleted = false
                    """)

    try:
        result = await db.execute(query, {"ids": ids})
        rows = result.fetchall()

        books = []
        for row in rows:
            book_id = row[0]
            current_smiles = row[5]
            mol_text_raw = row[8]  # Чистый текстовый мольфайл с координатами Actelion

            # Если mol_file_raw почему-то пустой, фолбэкаемся на обычный smiles-генератор
            if mol_text_raw:
                svg = generate_molecule_svg_from_molfile(mol_text_raw, book_id)
            else:
                svg = generate_molecule_svg_coordgen(current_smiles)

            books.append({
                "id": book_id,
                "external_id": row[1],
                "name": row[2],
                "book_name": row[3],
                "pages": row[4],
                "smiles": current_smiles,
                "references": row[6],
                "date_added": row[7].isoformat() if row[7] else None,
                "svg_content": svg
            })
        return books

    except Exception as e:
        print(f"Error fetching books by IDs: {e}")
        return []


from rdkit import Chem
from rdkit.Chem import Draw
from rdkit.Chem import rdDepictor


def generate_molecule_svg_coordgen(smiles: str) -> str:
    """
    Генерация качественного адаптивного SVG для одной молекулы (или смеси)
    с использованием улучшенного движка макетирования CoordGen.
    """
    if not smiles:
        return ""

    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            # 1. Включаем продвинутый движок генерации координат (как в Schrodinger/ChemDraw)
            rdDepictor.SetPreferCoordGen(True)

            # Сбрасываем старые конформации и генерируем идеальную 2D-сетку
            mol.RemoveAllConformers()
            rdDepictor.Compute2DCoords(mol)

            # 2. Инициализируем холст
            # Размеры холста задают базовое соотношение сторон (2:1)
            init_w, init_h = 400, 200
            d2d = Draw.MolDraw2DSVG(init_w, init_h)

            opts = d2d.drawOptions()
            opts.prepareMolsBeforeDrawing = True
            opts.fixedFontSize = 14
            opts.padding = 0.08  # Небольшой отступ, чтобы атомы не прижимались к краям холста

            # 3. Отрисовка
            d2d.DrawMolecule(mol)
            d2d.FinishDrawing()
            svg = d2d.GetDrawingText()

            # 4. Делаем SVG адаптивным через добавление viewBox.
            # Если просто заменить width/height на 100%, браузер может некорректно
            # масштабировать холст без указания соотношения сторон.
            if f'width="{init_w}px"' in svg:
                svg = svg.replace(
                    f'width="{init_w}px" height="{init_h}px"',
                    f'viewBox="0 0 {init_w} {init_h}" width="100%" height="auto"'
                )
            else:
                # На случай, если RDKit выдал строку без "px"
                svg = svg.replace(f'width="{init_w}"', 'width="100%"').replace(f'height="{init_h}"', 'height="auto"')

            return svg

    except Exception as e:
        print(f"RDKit Render Error (Molecule) for {smiles[:20]}: {e}")

    return ""


def generate_molecule_svg_from_molfile(mol_block: str, book_id: int) -> str:
    if not mol_block:
        return ""

    try:
        # 1. Парсим строго без санитизации, чтобы сохранить стерео-узы и сетку Actelion
        mol = Chem.MolFromMolBlock(mol_block, sanitize=False, removeHs=False)
        if not mol or mol.GetNumConformers() == 0:
            return ""

        # 2. Считаем только свойства/валентности атомов (защита от С++ Pre-condition падения)
        mol.UpdatePropertyCache(strict=False)

        # 3. Инициализируем холст фиксированного размера
        init_w, init_h = 400, 200
        d2d = Draw.MolDraw2DSVG(init_w, init_h)

        # Настройки отображения
        opts = d2d.drawOptions()
        opts.prepareMolsBeforeDrawing = False  # ЗАПРЕЩАЕМ RDKit менять координаты и генерировать свою сетку
        opts.fixedFontSize = 14
        opts.padding = 0.12

        # 4. Отрисовка конкретного конформера с родными координатами
        d2d.DrawMolecule(mol, confId=0)
        d2d.FinishDrawing()
        svg = d2d.GetDrawingText()

        # 5. Делаем SVG резиновым для фронтенда
        if f'width="{init_w}px"' in svg:
            return svg.replace(f'width="{init_w}px" height="{init_h}px"',
                               f'viewBox="0 0 {init_w} {init_h}" width="100%" height="auto"')
        return svg.replace(f'width="{init_w}"', 'width="100%"').replace(f'height="{init_h}"', 'height="auto"')

    except Exception as e:
        print(f"[RAW MOL RENDER ERROR {book_id}]: {e}")
        return ""