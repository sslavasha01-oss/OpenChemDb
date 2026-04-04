from rdkit import Chem
from rdkit.Chem import AllChem


def get_ketcher_ready_reaction(rxn_smiles: str):
    """
    Превращает SMILES реакции в набор 2D-координат (V2000 Molblock).
    Это единственный способ заставить Кетчер не рисовать 'кашу'.
    """
    sides = rxn_smiles.split('>>')
    parts_blocks = []

    for side in sides:
        mols = [Chem.MolFromSmiles(s) for s in side.split('.')]
        side_molblocks = []

        for mol in mols:
            if mol:
                # 1. Генерируем правильные 2D координаты силами RDKit
                AllChem.Compute2DCoords(mol)
                # 2. Делаем Mol-блок (текстовое описание координат каждого атома)
                side_molblocks.append(Chem.MolToMolBlock(mol))

        parts_blocks.append(side_molblocks)

    return parts_blocks


rxn_raw = "F[C@]1(Cl)[C@@](F)(Cl)[C@]2(F)[C@@](F)(Br)[C@@](F)(Br)[C@]12F.F[C@]1(Cl)[C@@](F)(Cl)[C@]2(F)[C@](F)(Br)[C@@](F)(Br)[C@]12F>>FC1=C(F)[C@]2(F)[C@@](F)(Cl)[C@@](F)(Cl)[C@]12F"

res = get_ketcher_ready_reaction(rxn_raw)

# Печатаем блок продукта (правая часть реакции)
print("--- MOL BLOCK ДЛЯ КЕТЧЕРА (ПРОДУКТ) ---")
print(res[1][0])