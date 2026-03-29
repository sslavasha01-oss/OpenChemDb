import asyncio
import csv
import os
import sys


from datetime import datetime, timezone
import asyncpg
from app.core.settings import settings

# Путь к твоему огромному файлу
CSV_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data/journal_db.txt")

async def fill_archive():
    print("Connecting to archive_db...")
    # Используем asyncpg напрямую для максимальной скорости
    conn = await asyncpg.connect(settings.ARCHIVE_DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

    try:
        print("Truncating table archive_reactions...")
        await conn.execute("TRUNCATE TABLE archive_reactions RESTART IDENTITY;")

        # Читаем TSV (судя по твоему образцу, там табуляция)
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')

            batch = []
            batch_size = 5000
            count = 0

            print("Starting data insertion...")
            for row in reader:
                # Подготовка кортежа данных для вставки
                # RDKit типы в Postgres принимают строку SMILES и сами конвертируют их
                record = (
                    int(float(row['ID'])),  # external_id
                    row['ROOT:REGNO'],
                    row['Dataset Name'],
                    row['Reaction Smiles'],  # Сохраняем как строку
                    row['DOI'],
                    row['reaction_raw'],  # Строка для отображения
                    row['reaction_raw'],  # Она же пойдет в тип REACTION
                    row['reaction_mapped'],  # Строка для отображения
                    row['reaction_mapped'],  # Она же пойдет в тип REACTION
                    row['is_mapped'].lower() == 'true',
                    row['mapping_source'],
                    row['Dataset Name 2'],
                    row['RXN:RXNREGNO'],
                    row['References'],
                    row['Conditions'],
                    row['Yield'],
                    "",  # procedure (пусто изначально)
                    False  # is_deleted
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
    # Используем специальный синтаксис вставки для RDKit типов
    # Мы передаем строку SMILES в колонки с типом REACTION, Postgres сам сделает каст
    query = """
            INSERT INTO archive_reactions ("external_id", "root_regno", "dataset_name", "reaction_smiles", "doi", \
                                           "reaction_raw_smiles", "reaction_raw_data", \
                                           "reaction_mapped_smiles", "reaction_mapped_data", \
                                           "is_mapped", "mapping_source", "dataset_name_2", "rxn_regno", \
                                           "references", "conditions", "yield_text", "procedure", "is_deleted") \
            VALUES ($1, $2, $3, $4, $5, $6, $7::reaction, $8, $9::reaction, $10, $11, $12, $13, $14, $15, $16, $17, $18) \
            """
    await conn.executemany(query, batch)


if __name__ == "__main__":
    asyncio.run(fill_archive())