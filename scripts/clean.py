from rdkit import Chem
from rdkit.Chem import AllChem


def fix_smiles(smiles_string):
    """
    Чистит и исправляет SMILES для корректного отображения.
    """
    if '>>' in smiles_string:
        # Если это реакция, чистим части по отдельности
        parts = smiles_string.split('>>')
        fixed_parts = [fix_smiles(p) for p in parts]
        return '>>'.join(fixed_parts)

    if '.' in smiles_string:
        # Если это смесь молекул, чистим каждую
        mols = smiles_string.split('.')
        fixed_mols = [fix_smiles(m) for m in mols]
        return '.'.join(fixed_mols)

    try:
        # 1. Попытка создать молекулу с санитарной обработкой
        mol = Chem.MolFromSmiles(smiles_string, sanitize=True)

        if mol is None:
            # 2. Если не вышло, пробуем создать без санитарии и исправить вручную
            mol = Chem.MolFromSmiles(smiles_string, sanitize=False)
            if mol:
                mol.UpdatePropertyCache(strict=False)
                # Исправляем типичные проблемы валентности (азот, сера)
                Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)

        if mol:
            # Возвращаем канонический SMILES без лишних символов
            return Chem.MolToSmiles(mol, isomericSmiles=True)
        else:
            return smiles_string  # Если совсем всё плохо, возвращаем как есть

    except Exception as e:
        return smiles_string


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

# Твой пример 1476879
raw_rxn = "CC(C)=[N+]=[N-].CCOCC.CC(O[C@H]1C=C[C@H]1OC(C)=O)=O>>CC(C)([C@H]1[C@H]2OC(C)=O)N=N[C@@H]1[C@@H]2OC(C)=O"
fixed_rxn = fix_reaction_string(raw_rxn)

print(f"Original: {raw_rxn}")
print(f"Fixed:    {fixed_rxn}")