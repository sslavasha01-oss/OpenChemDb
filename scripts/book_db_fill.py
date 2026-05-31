import sys
import os
import asyncio
import csv
import asyncpg
from rdkit import Chem  # Добавляем RDKit для проверки

from rdkit import RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

# Отключаем логирование предупреждений (Warnings) и ошибок (Errors) в RDKit
RDLogger.DisableLog('rdApp.warning')

# Пробиваем пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.settings import settings

CSV_FILE_PATH = os.path.join(BASE_DIR, "data/book_base_text.txt")


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
        # Этот шаг переведет гипервалентный хлор в правильную ионную форму
        mol = rdMolStandardize.Cleanup(mol)

        # 3. Теперь, когда хлор стандартизирован, можно прогнать полную санитизацию
        Chem.SanitizeMol(mol)

        # Возвращает системный каноничный SMILES (он будет с зарядами, но стабильный!)
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

        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            batch = []
            batch_size = 5000
            skipped_count = 0
            total_count = 0

            print("Starting validation and insertion...")
            for row in reader:
                smiles = row.get('Smiles', '').strip()
                if smiles.startswith('[?]'):
                    smiles = smiles[3:].strip()

                canonical_smiles = canonicalize_molecule_smiles(smiles)
                # Проверка валидности структуры
                if not canonical_smiles:
                    print(f"Skipping invalid SMILES (ID: {row.get('ID')}): {smiles}")
                    skipped_count += 1
                    continue

                try:
                    ext_id = int(float(row['ID'])) if row.get('ID') else 0

                    record = (
                        ext_id,
                        row.get('name'),
                        row.get('Book'),
                        row.get('Pages'),
                        canonical_smiles,
                        canonical_smiles,  # Для mol_data
                        row.get('references'),
                        False
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
    query = """
            INSERT INTO book_base (external_id, name, book_name, pages, smiles, mol_data, "references", is_deleted) \
            VALUES ($1, $2, $3, $4, $5, $6::mol, $7, $8) \
            """
    await conn.executemany(query, batch)


if __name__ == "__main__":
    asyncio.run(fill_books())