from rdkit import Chem
from rdkit.Chem import rdChemReactions

def process_chemical_input(raw_input: str):
    if not raw_input:
        return ""

    # 1. СЛУЧАЙ: Реакция (RXN block).
    # В них заголовок $RXN обычно идет с первой строки.
    if "$RXN" in raw_input:
        rxn = rdChemReactions.ReactionFromRxnBlock(raw_input)
        if rxn:
            return rdChemReactions.ReactionToSmarts(rxn)

    # 2. СЛУЧАЙ: Одна молекула (V2000 / V3000).
    # ВАЖНО: Не делаем .strip() до парсинга, чтобы не убить структуру строк!
    if "V2000" in raw_input or "V3000" in raw_input:
        mol = Chem.MolFromMolBlock(raw_input)
        if mol:
            try:
                Chem.SanitizeMol(mol) # Наша ароматизация
                query = Chem.MolToSmarts(mol)
                return ">>" + query
            except:
                return ">>" + Chem.MolToSmarts(mol)
        else:
            # Если не распарсилось, попробуем всё же убрать лишние пробелы
            # ТОЛЬКО по краям всего блока, но не внутри
            mol_retry = Chem.MolFromMolBlock(raw_input.strip())
            if mol_retry:
                Chem.SanitizeMol(mol_retry)
                return ">>" + Chem.MolToSmarts(mol_retry)
            return "Error: RDKit could not parse Molfile block"

    # 3. СЛУЧАЙ: Если это не спец-форматы, возвращаем как есть (SMILES)
    return raw_input.strip()

def process_search_request(raw_input: str):
    # 1. Проверяем, не Molfile ли это (Ketcher V2000)
    if "V2000" in raw_input:
        # RDKit очень чувствителен к структуре Molfile
        mol = Chem.MolFromMolBlock(raw_input)

        if mol:
            try:
                # 2. ВОТ ОНА - АРОМАТИЗАЦИЯ!
                # RDKit посмотрит на 1=2-3=4 и сам сделает из них бензол
                Chem.SanitizeMol(mol)

                # 3. Генерируем SMARTS, который поймет база (с двоеточиями)
                query = Chem.MolToSmarts(mol)
                return ">>" + query
            except:
                # Если санитизация упала (бывает на сложной химии),
                # пробуем отдать как есть
                return ">>" + Chem.MolToSmarts(mol)
        else:
            return "Error: RDKit could not parse Molfile"

    # Если это обычный SMILES
    return raw_input


# ТЕСТ С ТВОИМИ ДАННЫМИ (правильно отформатированными)
test_molfile = ("""
-INDIGO-04052622372D

  6  6  0  0  0  0  0  0  0  0999 V2000
    5.1848   -4.6251    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    6.9152   -4.6246    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    6.0516   -4.1250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    6.9152   -5.6255    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    5.1848   -5.6300    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    6.0538   -6.1250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  3  1  2  0  0  0  0
  1  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  4  1  0  0  0  0
  4  2  2  0  0  0  0
  2  3  1  0  0  0  0
M  END

"""
)
