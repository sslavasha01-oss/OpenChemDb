from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import BigInteger, Integer, Text, Numeric, DateTime, func, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import UserDefinedType

from app.core.db import Base


# Кастомные типы RDKit
class MolType(UserDefinedType):
    cache_ok = True
    def get_col_spec(self, **kw): return "MOL"

class ReactionType(UserDefinedType):
    cache_ok = True
    def get_col_spec(self, **kw): return "REACTION"

class UserJournal(Base):
    __tablename__ = 'user_journal'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    external_id: Mapped[int] = mapped_column(Integer, nullable=False)

    date_added: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    date_modified: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Product
    product_smiles: Mapped[Optional[str]] = mapped_column(Text)
    product_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    product_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    product_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    product_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), server_default='1.0')
    product_theoretical_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    product_praktical_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    product_yield_calc: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Reactions
    reaction_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reaction_mapped_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reaction_mol_data: Mapped[Optional[any]] = mapped_column(ReactionType)
    reaction_mol_mapped_data: Mapped[Optional[any]] = mapped_column(ReactionType)

    # Reagents 1-5
    # Reagent 1
    reagent1_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reagent1_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    reagent1_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    reagent1_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent1_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent1_density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    reagent1_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), server_default='1.0')
    reagent1_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent1_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Reagent 2
    reagent2_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reagent2_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    reagent2_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    reagent2_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent2_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent2_density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    reagent2_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), server_default='1.0')
    reagent2_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent2_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Reagent 3
    reagent3_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reagent3_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    reagent3_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    reagent3_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent3_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent3_density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    reagent3_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), server_default='1.0')
    reagent3_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent3_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Reagent 4
    reagent4_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reagent4_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    reagent4_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    reagent4_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent4_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent4_density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    reagent4_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), server_default='1.0')
    reagent4_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent4_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Reagent 5
    reagent5_smiles: Mapped[Optional[str]] = mapped_column(Text)
    reagent5_mol_data: Mapped[Optional[any]] = mapped_column(MolType)
    reagent5_moles: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 6))
    reagent5_molar_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent5_mass: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent5_density: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    reagent5_concentration: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), server_default='1.0')
    reagent5_volume: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    reagent5_molar_ekv: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    # Meta
    conditions: Mapped[Optional[str]] = mapped_column(Text)
    referenced_record_external_id: Mapped[Optional[int]] = mapped_column(Integer)
    references: Mapped[Optional[str]] = mapped_column(Text)
    doi: Mapped[Optional[str]] = mapped_column(Text)
    procedure: Mapped[Optional[str]] = mapped_column(Text)