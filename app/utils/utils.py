from rdkit import Chem
from rdkit.Chem import AllChem

def canonicalize_smiles(smiles: str):
    """
    Приводит SMILES к каноничному ароматизированному виду.
    Работает как для одиночных молекул, так и для реакций.
    """
    try:
        if ">>" in smiles:
            # Если это реакция, разбиваем, ароматизируем части и собираем назад
            parts = smiles.split(">>")
            new_parts = []
            for p in parts:
                if not p:
                    new_parts.append("")
                    continue
                mol = Chem.MolFromSmiles(p)
                if mol:
                    Chem.SanitizeMol(mol) # Это делает ароматизацию
                    new_parts.append(Chem.MolToSmiles(mol))
                else:
                    new_parts.append(p)
            return ">>".join(new_parts)
        else:
            # Для одиночной молекулы
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                Chem.SanitizeMol(mol)
                return Chem.MolToSmiles(mol)
    except:
        return smiles
    return smiles