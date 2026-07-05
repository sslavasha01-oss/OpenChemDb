import asyncio
import csv
import os
import sys


from datetime import datetime, timezone
import asyncpg
from app.core.settings import settings

# Путь к твоему огромному файлу
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/fullDb.dwar")

from rdkit import Chem


def sanitize_raw_smiles(smiles: str) -> str:
    """
    Нормализует SMILES без удаления маппинга.
    Исправляет ошибки валентности и канонизирует структуру.
    """
    if not smiles or not isinstance(smiles, str):
        return ""

    try:
        # Пробуем создать молекулу. Sanitize=False позволяет прочитать "битые" структуры
        mol = Chem.MolFromSmiles(smiles, sanitize=False)
        if mol:
            # Исправляем валентности (особенно важно для азота и металлов)
            mol.UpdatePropertyCache(strict=False)
            # Базовая очистка (ароматика, стерео, кекилизация)
            Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)
            # Возвращаем чистый SMILES.
            # isomericSmiles=True сохранит твою стереохимию [C@H]
            return Chem.MolToSmiles(mol, isomericSmiles=True)
        return smiles
    except Exception:
        # Если RDKit совсем не смог — возвращаем оригинал, пусть Postgres сам решит
        return smiles


def fix_reaction_string(reaction_smiles: str) -> str:
    """Разбивает реакцию на части и санирует каждую молекулу отдельно"""
    if '>>' not in reaction_smiles:
        return sanitize_raw_smiles(reaction_smiles)

    parts = reaction_smiles.split('>>')
    left = '.'.join([sanitize_raw_smiles(s) for s in parts[0].split('.')])
    right = '.'.join([sanitize_raw_smiles(s) for s in parts[1].split('.')])
    return f"{left}>>{right}"

async def fill_archive():
    print("Connecting to archive_db...")
    # Используем asyncpg напрямую для максимальной скорости
    conn = await asyncpg.connect(settings.ARCHIVE_DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

    try:
        print("Truncating table archive_reactions...")
        await conn.execute("TRUNCATE TABLE archive_reactions RESTART IDENTITY;")

        # Вместо open() используем наш генератор, отсекающий мусор
        clean_lines = clean_dwar_file_lines(CSV_FILE_PATH)
        reader = csv.DictReader(clean_lines, delimiter='\t')

        batch = []
        batch_size = 5000
        count = 0

        print("Starting data insertion...")
        for row in reader:
            raw_smi = row['reaction_raw']
            fixed_raw_smi = fix_reaction_string(raw_smi)

            record = (
                int(float(row['ID'])),  # $1  -> external_id
                row['ROOT:REGNO'],  # $2  -> root_regno
                row['Dataset Name'],  # $3  -> dataset_name
                row['Reaction Smiles'],  # $4  -> reaction_smiles
                row['DOI'],  # $5  -> doi
                fixed_raw_smi,  # $6  -> reaction_raw_smiles
                fixed_raw_smi,  # $7  -> reaction_raw_data (каст в ::reaction)
                row['reaction_mapped'],  # $8  -> reaction_mapped_smiles
                row['reaction_mapped'],  # $9  -> reaction_mapped_data (каст в ::reaction)
                row['is_mapped'].lower() == 'true',  # $10 -> is_mapped
                row['mapping_source'],  # $11 -> mapping_source
                row['Dataset Name 2'],  # $12 -> dataset_name_2
                row['RXN:RXNREGNO'],  # $13 -> rxn_regno
                row['References'],  # $14 -> references
                row['Conditions'],  # $15 -> conditions
                row['Yield'],  # $16 -> yield_text
                "",  # $17 -> procedure
                False,  # $18 -> is_deleted
                row.get('Reaction', ''),  # $19 -> dwar_rxncode
                row.get('idcoordinates2D', ''),  # $20 -> dwar_coordinates
                ""  # $21 -> raw_rxn_file
            )
            batch.append(record)

            if len(batch) >= batch_size:
                await insert_batch(conn, batch)
                batch = []
                count += batch_size
                print(f"Processed {count} rows...")

        # Остатки
        if batch:
            await insert_batch(conn, batch)
            print(f"Total processed: {count + len(batch)}")

    finally:
        await conn.close()


async def insert_batch(conn, batch):
    query = """
            INSERT INTO archive_reactions (
                "external_id", "root_regno", "dataset_name", "reaction_smiles", "doi", 
                "reaction_raw_smiles", "reaction_raw_data", 
                "reaction_mapped_smiles", "reaction_mapped_data", 
                "is_mapped", "mapping_source", "dataset_name_2", "rxn_regno", 
                "references", "conditions", "yield_text", "procedure", "is_deleted",
                "dwar_rxncode", "dwar_coordinates", "raw_rxn_file"
            ) 
            VALUES (
                $1, $2, $3, $4, $5, $6, $7::reaction, $8, $9::reaction, 
                $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
            ) 
            """
    await conn.executemany(query, batch)


def clean_dwar_file_lines(file_path):
    """
    Читает файл DataWarrior, пропускает XML-подобные хедеры и пустые строки,
    возвращая только строки с реальными данными (начиная со строки заголовков).
    """
    with open(file_path, mode='r', encoding='utf-8') as f:
        in_headers = True
        for line in f:
            stripped = line.strip()
            # Пропускаем XML-теги DataWarrior
            if stripped.startswith('<') and stripped.endswith('>'):
                continue
            if not stripped:
                continue
            # Первой валидной строкой без тегов будет строка с названиями колонок
            yield line

if __name__ == "__main__":
    asyncio.run(fill_archive())