import asyncio
from ftplib import print_line

import asyncpg
from rdkit import Chem
from app.core.settings import settings

# Настройки производительности для 18 ядер и 3 млн строк
BATCH_SIZE = 1000  # Размер пачки для UPDATE


async def get_mol_parts(reaction_smiles: str):
    """
    Разбивает SMILES реакции на реагенты и продукты.
    Возвращает (reactants_smiles, products_smiles)
    """
    if not reaction_smiles or '>>' not in reaction_smiles:
        return None, None

    try:
        parts = reaction_smiles.split('>>')
        reactants = parts[0] if parts[0].strip() else None
        # Продукты — это всё, что после второй стрелки (если она есть) или после первой
        # В формате SMILES: A.B>>C.D
        products = parts[-1] if parts[-1].strip() else None

        return reactants, products
    except Exception:
        print_line("Error while parsing SMILES:" + reaction_smiles)
        return None, None


async def migrate_mol_columns():
    print(f"[{datetime.now()}] Starting migration of 3M records...")

    # Подключение к БД
    conn = await asyncpg.connect(settings.ARCHIVE_DATABASE_URL.replace("postgresql+asyncpg", "postgresql"))

    try:
        # Считаем общее количество для прогресс-бара
        total = await conn.fetchval("SELECT count(*) FROM archive_reactions WHERE mol_products IS NULL")
        print(f"Total rows to process: {total}")

        offset = 0
        while True:
            # 1. Берем пачку записей, где колонки еще не заполнены
            # Используем reaction_raw_smiles, так как это готовая строка
            rows = await conn.fetch(
                """
                SELECT id, reaction_raw_smiles 
                FROM archive_reactions 
                WHERE mol_products IS NULL 
                LIMIT $1
                """, BATCH_SIZE
            )

            if not rows:
                break

            update_data = []
            for row in rows:
                r_smi, p_smi = await get_mol_parts(row['reaction_raw_smiles'])
                # Готовим данные для executemany
                # (mol_reactants, mol_products, id)
                update_data.append((r_smi, p_smi, row['id']))

            # 2. Массовое обновление
            # Используем каст ::mol, чтобы Postgres сам превратил строку в тип RDKit
            await conn.executemany(
                """
                UPDATE archive_reactions 
                SET mol_reactants = $1::mol, 
                    mol_products = $2::mol 
                WHERE id = $3
                """, update_data
            )

            offset += len(rows)
            if offset % 50000 == 0:
                print(f"[{datetime.now()}] Processed {offset}/{total}...")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    from datetime import datetime

    asyncio.run(migrate_mol_columns())