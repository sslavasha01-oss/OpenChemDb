from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from decimal import Decimal
from datetime import datetime


class UserJournalSchema(BaseModel):
    # Позволяет Pydantic читать данные напрямую из SQLAlchemy объектов
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    user_id: Optional[int] = None
    external_id: Optional[int] = None
    date_added: Optional[datetime] = None
    date_modified: Optional[datetime] = None

    # Product (без mol_data)
    product_smiles: Optional[str] = None
    product_molar_mass: Optional[Decimal] = None
    product_moles: Optional[Decimal] = None
    product_molar_ekv: Optional[Decimal] = None
    product_theoretical_mass: Optional[Decimal] = None
    product_praktical_mass: Optional[Decimal] = None
    product_yield_calc: Optional[Decimal] = None
    product_name: Optional[str] = None

    # Reaction (без mol_data)
    reaction_smiles: Optional[str] = None
    reaction_mapped_smiles: Optional[str] = None

    # Reagents 1-5 (только smiles и расчетные данные)
    # Повторяем структуру для каждого реагента
    reagent1_smiles: Optional[str] = None
    reagent1_moles: Optional[Decimal] = None
    reagent1_molar_mass: Optional[Decimal] = None
    reagent1_mass: Optional[Decimal] = None
    reagent1_density: Optional[Decimal] = None
    reagent1_concentration: Optional[Decimal] = None
    reagent1_volume: Optional[Decimal] = None
    reagent1_molar_ekv: Optional[Decimal] = None
    reagent1_name: Optional[str] = None

    reagent2_smiles: Optional[str] = None
    reagent2_moles: Optional[Decimal] = None
    reagent2_molar_mass: Optional[Decimal] = None
    reagent2_mass: Optional[Decimal] = None
    reagent2_density: Optional[Decimal] = None
    reagent2_concentration: Optional[Decimal] = None
    reagent2_volume: Optional[Decimal] = None
    reagent2_molar_ekv: Optional[Decimal] = None
    reagent2_name: Optional[str] = None

    reagent3_smiles: Optional[str] = None
    reagent3_moles: Optional[Decimal] = None
    reagent3_molar_mass: Optional[Decimal] = None
    reagent3_mass: Optional[Decimal] = None
    reagent3_density: Optional[Decimal] = None
    reagent3_concentration: Optional[Decimal] = None
    reagent3_volume: Optional[Decimal] = None
    reagent3_molar_ekv: Optional[Decimal] = None
    reagent3_name: Optional[str] = None

    reagent4_smiles: Optional[str] = None
    reagent4_moles: Optional[Decimal] = None
    reagent4_molar_mass: Optional[Decimal] = None
    reagent4_mass: Optional[Decimal] = None
    reagent4_density: Optional[Decimal] = None
    reagent4_concentration: Optional[Decimal] = None
    reagent4_volume: Optional[Decimal] = None
    reagent4_molar_ekv: Optional[Decimal] = None
    reagent4_name: Optional[str] = None

    reagent5_smiles: Optional[str] = None
    reagent5_moles: Optional[Decimal] = None
    reagent5_molar_mass: Optional[Decimal] = None
    reagent5_mass: Optional[Decimal] = None
    reagent5_density: Optional[Decimal] = None
    reagent5_concentration: Optional[Decimal] = None
    reagent5_volume: Optional[Decimal] = None
    reagent5_molar_ekv: Optional[Decimal] = None
    reagent5_name: Optional[str] = None

    # Meta
    conditions: Optional[str] = None
    referenced_record_external_id: Optional[int] = None
    references: Optional[str] = None
    doi: Optional[str] = None
    procedure: Optional[str] = None