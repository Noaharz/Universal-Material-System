"""Shared helpers for the UMS definition models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..units import Quantity, try_quantity


@dataclass
class Identity:
    """Common identity block shared by all resource types."""

    resource_id: str
    name: str
    version: int = 1
    category: Optional[str] = None

    def to_section(self) -> Dict[str, Any]:
        section: Dict[str, Any] = {"Id": self.resource_id, "Name": self.name}
        if self.category:
            section["Category"] = self.category
        return section


def as_int(value: Any, default: int = 1) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default


def as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def quantity_map(mapping: Any) -> Dict[str, Any]:
    """Coerce scalar values in a mapping to quantities where possible.

    Structured values (model references, nested blocks) are preserved verbatim.
    """
    result: Dict[str, Any] = {}
    if not isinstance(mapping, dict):
        return result
    for key, value in mapping.items():
        if isinstance(value, dict):
            result[key] = value
        else:
            quantity = try_quantity(value)
            result[key] = quantity if quantity is not None else value
    return result


def scalar_to_primitive(value: Any) -> Any:
    """Convert a :class:`Quantity` back to a serializable primitive."""
    if isinstance(value, Quantity):
        if value.unit.is_dimensionless:
            return value.value
        return f"{value.value:g} {value.unit.symbol}"
    return value


def identity_from_sections(sections: Dict[str, Any]) -> Identity:
    identity_section = sections.get("Identity") or {}
    if not isinstance(identity_section, dict):
        identity_section = {}
    return Identity(
        resource_id=as_str(identity_section.get("Id") or identity_section.get("ResourceId")),
        name=as_str(identity_section.get("Name")),
        version=as_int(sections.get("Version", identity_section.get("Version")), 1),
        category=identity_section.get("Category"),
    )
