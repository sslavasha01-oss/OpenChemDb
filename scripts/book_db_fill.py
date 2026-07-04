import sys
import os
import asyncio
import csv
import asyncpg
from rdkit import Chem

from rdkit import RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

# Отключаем логирование предупреждений (Warnings) и ошибок (Errors) в RDKit
RDLogger.DisableLog('rdApp.warning')

# Пробиваем пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.settings import settings

# Путь к новому файлу DataWarrior с колонкой Smiles
DATAWARRIOR_FILE_PATH = os.path.join(BASE_DIR, "data/book_base.dwar")


def canonicalize_molecule_smiles(smi: str):
    """
    Стандартизирует молекулу по правилам RDKit.
    Переводит Cl(=O)=O в ионную форму корректно, сохраняя всю остальную структуру.
    """
    if not smi:
        return None
    try:
        # 1. Читаем БЕЗ санитизации, чтобы не упасть на старте
        mol = Chem.MolFromSmiles(smi, sanitize=False)
        if mol is None:
            return None

        # 2. Очищаем структуру стандартными инструментами RDKit
        mol = rdMolStandardize.Cleanup(mol)

        # 3. Теперь, когда хлор стандартизирован, можно прогнать полную санитизацию
        Chem.SanitizeMol(mol)

        # Возвращает системный каноничный SMILES
        return Chem.MolToSmiles(mol, canonical=True)
    except Exception:
        pass
    return None


async def fill_books():
    print("Connecting to archive_db...")
    conn = await asyncpg.connect(settings.ARCHIVE_DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

    try:
        print("Truncating table book_base...")
        await conn.execute("TRUNCATE TABLE book_base RESTART IDENTITY;")

        with open(DATAWARRIOR_FILE_PATH, mode='r', encoding='utf-8') as f:
            # Пропускаем служебные мета-заголовки DataWarrior до строки с названиями колонок
            lines_skipped = 0
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                # Ищем строку заголовков по ключевым колонкам DataWarrior
                if "idcoordinates2D" in line and "Structure" in line:
                    f.seek(pos)  # Возвращаем указатель на начало строки заголовков для DictReader
                    break
                lines_skipped += 1

            print(f"Skipped {lines_skipped} metadata lines. Parsing TSV...")

            reader = csv.DictReader(f, delimiter='\t')

            batch = []
            batch_size = 5000
            skipped_count = 0
            total_count = 0

            print("Starting validation and insertion...")
            for row in reader:
                # Если строка пустая или DictReader поймал метаданные в конце файла
                if not row or not any(row.values()):
                    continue

                # Безопасно достаем SMILES (если ключа нет или там None -> будет пустая строка)
                smiles = (row.get('Smiles') or '').strip()

                # Если это техническая строка DataWarrior в конце файла (например, содержит теги)
                if not smiles and not row.get('Structure') and not row.get('ID'):
                    continue

                if smiles.startswith('[?]'):
                    smiles = smiles[3:].strip()

                canonical_smiles = canonicalize_molecule_smiles(smiles)
                # Проверка валидности структуры
                if not canonical_smiles:
                    print(f"Skipping invalid SMILES (ID: {row.get('ID')}): {smiles}")
                    skipped_count += 1
                    continue

                # Достаем данные для восстановления геометрии
                idcode = (row.get('Structure') or '').strip()
                id_coords_2d = (row.get('idcoordinates2D') or '').strip()

                # Заменяем теги <NL> на реальные переносы строк для текстовых полей
                book_field = (row.get('Book') or '').replace('<NL>', '\n')
                pages_field = (row.get('Pages') or '').replace('<NL>', '\n')
                refs_field = (row.get('references') or '').replace('<NL>', '\n')

                try:
                    # Проверяем ID, если это не число (или тег в конце файла) — скипаем
                    id_val = row.get('ID')
                    if not id_val or id_val.startswith('<'):
                        continue

                    ext_id = int(float(id_val))

                    record = (
                        ext_id,
                        row.get('name'),
                        book_field,
                        pages_field,
                        canonical_smiles,
                        canonical_smiles,  # Для mol_data (в тип mol)
                        refs_field,
                        False,
                        idcode,  # Новое поле
                        id_coords_2d,  # Новое поле
                        None  # mol_file (пока пустой)
                    )
                    batch.append(record)
                    total_count += 1
                except (ValueError, TypeError) as e:
                    print(f"Error processing row ID {row.get('ID')}: {e}")
                    continue

                if len(batch) >= batch_size:
                    await insert_batch(conn, batch)
                    batch = []
                    print(f"Inserted {total_count} records...")

            if batch:
                await insert_batch(conn, batch)

        print(f"\n--- Finish ---")
        print(f"Successfully inserted: {total_count}")
        print(f"Skipped invalid records: {skipped_count}")

    finally:
        await conn.close()


async def insert_batch(conn, batch):
    # Запрос адаптирован под новые колонки, mol_file временно пишется как NULL (тип mol)
    query = """
            INSERT INTO book_base (
                external_id, name, book_name, pages, smiles, mol_data, 
                "references", is_deleted, idcode, id_coords_2d, mol_file
            ) \
            VALUES ($1, $2, $3, $4, $5, $6::mol, $7, $8, $9, $10, $11::mol) \
            """
    await conn.executemany(query, batch)


if __name__ == "__main__":
    asyncio.run(fill_books())