from rdkit import Chem


def fix_full_reaction(rxn_smiles: str) -> str:
    """
    Разбивает реакцию, лечит каждую молекулу и собирает обратно.
    """
    if '>>' not in rxn_smiles:
        return "Это не реакция (нет >>)"

    # Разделяем на левую (реагенты) и правую (продукты) части
    sides = rxn_smiles.split('>>')
    fixed_sides = []

    for side in sides:
        # В каждой части может быть несколько молекул через точку
        mols_smiles = side.split('.')
        fixed_mols = []

        for smi in mols_smiles:
            # 1. Читаем молекулу. Sanitize=True заставит RDKit пересчитать всё по-честному
            mol = Chem.MolFromSmiles(smi, sanitize=True)
            if mol:
                # 2. Генерируем канонический SMILES.
                # Это перестроит индексы C1, C2 так, чтобы они не конфликтовали
                fixed_smi = Chem.MolToSmiles(mol, isomericSmiles=True, canonical=True)
                fixed_mols.append(fixed_smi)
            else:
                # Если совсем плохо — оставляем как было, но помечаем
                fixed_mols.append(smi)

        # Собираем молекулы обратно через точку
        fixed_sides.append('.'.join(fixed_mols))

    # Собираем финальную реакцию
    return '>>'.join(fixed_sides)


# Ваша реакция со скриншота (с кучей галогенов и бициклами)
rxn_raw = "F[C@]1(Cl)[C@@](F)(Cl)[C@]2(F)[C@@](F)(Br)[C@@](F)(Br)[C@]12F.F[C@]1(Cl)[C@@](F)(Cl)[C@]2(F)[C@](F)(Br)[C@@](F)(Br)[C@]12F>>FC1=C(F)[C@]2(F)[C@@](F)(Cl)[C@@](F)(Cl)[C@]12F"

fixed_rxn = fix_full_reaction(rxn_raw)
print(rxn_raw)
print("--- ИСПРАВЛЕННАЯ РЕАКЦИЯ ---")
print(fixed_rxn)