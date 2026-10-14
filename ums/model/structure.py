"""The ``.structure`` universal structure definition.

A structure is deliberately not limited to molecules. The ``StructureType``
selects which sections are meaningful: Molecular, Crystal, Ionic, Polymer,
Network, Amorphous, Porous, Composite or a user-defined type.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import Identity, as_str, identity_from_sections, quantity_map


class StructureType(enum.Enum):
    MOLECULAR = "Molecular"
    CRYSTAL = "Crystal"
    IONIC = "Ionic"
    POLYMER = "Polymer"
    NETWORK = "Network"
    AMORPHOUS = "Amorphous"
    POROUS = "Porous"
    COMPOSITE = "Composite"
    CUSTOM = "Custom"

    @classmethod
    def parse(cls, value: Any) -> "StructureType":
        if value is None:
            return cls.CUSTOM
        text = str(value).strip()
        for member in cls:
            if member.value.lower() == text.lower():
                return member
        return cls.CUSTOM


KNOWN_SECTIONS = {
    "Version",
    "Identity",
    "Composition",
    "Topology",
    "Geometry",
    "Crystal",
    "Periodicity",
    "Models",
    "References",
    "Substructures",
}


@dataclass
class StructureDefinition:
    identity: Identity
    structure_type: StructureType = StructureType.CUSTOM
    composition: List[Dict[str, Any]] = field(default_factory=list)
    topology: Dict[str, Any] = field(default_factory=dict)
    geometry: Dict[str, Any] = field(default_factory=dict)
    crystal: Dict[str, Any] = field(default_factory=dict)
    periodicity: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, Any] = field(default_factory=dict)
    references: Dict[str, Any] = field(default_factory=dict)
    substructures: List[Any] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
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
    def atoms(self) -> List[Dict[str, Any]]:
        value = self.topology.get("Atoms")
        return value if isinstance(value, list) else []

    @property
    def bonds(self) -> List[Dict[str, Any]]:
        value = self.topology.get("Bonds")
        return value if isinstance(value, list) else []

    def atom_refs(self) -> List[str]:
        """Return the logical resource paths of all referenced atom definitions."""
        refs: List[str] = []
        for entry in self.composition:
            if isinstance(entry, dict):
                ref = entry.get("AtomRef") or entry.get("Ref")
                if ref:
                    refs.append(str(ref))
        for atom in self.atoms:
            ref = atom.get("Type") if isinstance(atom, dict) else None
            if ref:
                refs.append(str(ref))
        for ref in self.references.get("AtomDefinitions", []) or []:
            refs.append(str(ref))
        seen: List[str] = []
        for ref in refs:
            if ref not in seen:
                seen.append(ref)
        return seen

    @classmethod
    def from_sections(cls, sections: Dict[str, Any], source_path: Optional[str] = None) -> "StructureDefinition":
        identity = identity_from_sections(sections)
        identity_section = sections.get("Identity") or {}
        if not isinstance(identity_section, dict):
            identity_section = {}
        composition = sections.get("Composition") or []
        if isinstance(composition, dict):
            composition = [composition]
        topology = sections.get("Topology") or {}
        if not isinstance(topology, dict):
            topology = {}
        return cls(
            identity=identity,
            structure_type=StructureType.parse(identity_section.get("StructureType")),
            composition=list(composition),
            topology=dict(topology),
            geometry=quantity_map(sections.get("Geometry")),
            crystal=quantity_map(sections.get("Crystal")),
            periodicity=dict(sections.get("Periodicity") or {}),
            models=dict(sections.get("Models") or {}),
            references=dict(sections.get("References") or {}),
            substructures=list(sections.get("Substructures") or []),
            extra={k: v for k, v in sections.items() if k not in KNOWN_SECTIONS},
            source_path=source_path,
        )

    def to_sections(self) -> Dict[str, Any]:
        from .base import scalar_to_primitive

        identity_section: Dict[str, Any] = {
            "Id": self.id,
            "Name": self.name,
            "StructureType": self.structure_type.value,
        }
        sections: Dict[str, Any] = {"Version": self.version, "Identity": identity_section}
        if self.composition:
            sections["Composition"] = self.composition
        if self.topology:
            sections["Topology"] = self.topology
        if self.geometry:
            sections["Geometry"] = {k: scalar_to_primitive(v) for k, v in self.geometry.items()}
        if self.crystal:
            sections["Crystal"] = {k: scalar_to_primitive(v) for k, v in self.crystal.items()}
        if self.periodicity:
            sections["Periodicity"] = self.periodicity
        if self.models:
            sections["Models"] = self.models
        if self.references:
            sections["References"] = self.references
        if self.substructures:
            sections["Substructures"] = self.substructures
        for key, value in self.extra.items():
            sections[key] = value
        return sections

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "structure",
            "id": self.id,
            "name": self.name,
            "structure_type": self.structure_type.value,
            "version": self.version,
            "composition": self.composition,
            "topology": self.topology,
            "geometry": {k: str(v) for k, v in self.geometry.items()},
            "crystal": {k: str(v) for k, v in self.crystal.items()},
            "periodicity": self.periodicity,
            "models": self.models,
            "references": self.references,
            "extra": self.extra,
            "source_path": self.source_path,
        }

    def __repr__(self) -> str:
        return f"StructureDefinition(id={self.id!r}, type={self.structure_type.value!r})"
