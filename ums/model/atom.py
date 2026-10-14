"""The ``.atom`` atom-type definition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..parser import coerce_quantity
from ..units import Quantity
from .base import Identity, as_int, identity_from_sections, quantity_map


@dataclass
class AtomDefinition:
    """Describes an atomic type (element), not a concrete atom in a scene."""

    identity: Identity
    symbol: Optional[str] = None
    atomic_number: Optional[int] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    electronic: Dict[str, Any] = field(default_factory=dict)
    nuclear: Dict[str, Any] = field(default_factory=dict)
    physical: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, Any] = field(default_factory=dict)
    references: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None

    @property
    def id(self) -> str:
        return self.identity.resource_id

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def version(self) -> int:
        return self.identity.version

    @property
    def atomic_mass(self) -> Optional[Quantity]:
        value = self.properties.get("AtomicMass")
        return value if isinstance(value, Quantity) else coerce_quantity(value)

    @property
    def isotopes(self) -> List[Any]:
        value = self.nuclear.get("Isotopes")
        return value if isinstance(value, list) else []

    @classmethod
    def from_sections(cls, sections: Dict[str, Any], source_path: Optional[str] = None) -> "AtomDefinition":
        identity = identity_from_sections(sections)
        identity_section = sections.get("Identity") or {}
        if not isinstance(identity_section, dict):
            identity_section = {}
        return cls(
            identity=identity,
            symbol=identity_section.get("Symbol"),
            atomic_number=as_int(identity_section.get("AtomicNumber"), 0) or None,
            properties=quantity_map(sections.get("Properties")),
            electronic=dict(sections.get("Electronic") or {}),
            nuclear=dict(sections.get("Nuclear") or {}),
            physical=dict(sections.get("Physical") or {}),
            models=dict(sections.get("Models") or {}),
            references=dict(sections.get("References") or {}),
            source_path=source_path,
        )

    def to_sections(self) -> Dict[str, Any]:
        from .base import scalar_to_primitive

        identity_section: Dict[str, Any] = {"Id": self.id, "Name": self.name}
        if self.symbol:
            identity_section["Symbol"] = self.symbol
        if self.atomic_number is not None:
            identity_section["AtomicNumber"] = self.atomic_number
        sections: Dict[str, Any] = {"Version": self.version, "Identity": identity_section}
        for name, block in (
            ("Properties", self.properties),
            ("Electronic", self.electronic),
            ("Nuclear", self.nuclear),
            ("Physical", self.physical),
            ("Models", self.models),
            ("References", self.references),
        ):
            if block:
                sections[name] = {k: scalar_to_primitive(v) for k, v in block.items()}
        return sections

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "atom",
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "atomic_number": self.atomic_number,
            "version": self.version,
            "properties": {k: str(v) if isinstance(v, Quantity) else v for k, v in self.properties.items()},
            "electronic": self.electronic,
            "nuclear": self.nuclear,
            "physical": self.physical,
            "models": self.models,
            "references": self.references,
            "source_path": self.source_path,
        }

    def __repr__(self) -> str:
        return f"AtomDefinition(id={self.id!r}, symbol={self.symbol!r})"
