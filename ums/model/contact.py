"""The ``Contact`` section of a material definition.

Contact physics describes how a material behaves when it touches another one:
friction and restitution together with the combine rules used to blend the two
materials' values. The field names match the common rigid-body engine
convention, so a host can map them directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

COMBINE_MODES = ("Average", "Minimum", "Multiply", "Maximum", "GeometricMean")


def _defaults() -> Dict[str, Any]:
    return {
        "StaticFriction": 0.6,
        "DynamicFriction": 0.5,
        "Restitution": 0.1,
        "FrictionCombine": "GeometricMean",
        "RestitutionCombine": "Maximum",
    }


@dataclass
class Contact:
    """Surface contact parameters (friction, restitution and combine rules)."""

    values: Dict[str, Any] = field(default_factory=dict)
    present: bool = False

    DEFAULTS = _defaults()

    def get(self, name: str, default: Any = None) -> Any:
        if name in self.values:
            return self.values[name]
        if default is not None:
            return default
        return self.DEFAULTS.get(name)

    def has(self, name: str) -> bool:
        return name in self.values

    @classmethod
    def from_sections(cls, section: Any) -> "Contact":
        if not isinstance(section, dict):
            return cls()
        return cls(values=dict(section), present=True)

    def to_sections(self) -> Dict[str, Any]:
        return dict(self.values)

    def merge(self, override: Any) -> "Contact":
        if not isinstance(override, dict) or not override:
            return self
        values = dict(self.values)
        values.update(override)
        return Contact(values=values, present=True)

    def to_dict(self) -> Dict[str, Any]:
        return {"present": self.present, "values": self.values}

    def __bool__(self) -> bool:
        return self.present


@dataclass
class ContactPair:
    """An override of the contact parameters against one specific material."""

    other: str
    values: Dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        if name in self.values:
            return self.values[name]
        return Contact.DEFAULTS.get(name) if default is None else default

    @classmethod
    def from_sections(cls, section: Any) -> "ContactPair":
        if not isinstance(section, dict):
            return cls(other="")
        values = {k: v for k, v in section.items() if k not in ("Other", "Material", "Ref")}
        other = section.get("Other") or section.get("Material") or section.get("Ref") or ""
        return cls(other=str(other), values=values)

    def to_sections(self) -> Dict[str, Any]:
        section: Dict[str, Any] = {}
        if self.other:
            section["Other"] = self.other
        section.update(self.values)
        return section


def contact_pairs_from_sections(section: Any) -> List[ContactPair]:
    if isinstance(section, dict):
        section = [section]
    if not isinstance(section, list):
        return []
    pairs: List[ContactPair] = []
    for entry in section:
        if isinstance(entry, dict):
            pairs.append(ContactPair.from_sections(entry))
    return pairs


def contact_pairs_to_sections(pairs: List[ContactPair]) -> List[Dict[str, Any]]:
    return [pair.to_sections() for pair in pairs]
