"""Material instances and mixes.

A material instance is a concrete use of a material definition in a scene, CAD
model or simulation. It stores a reference to the (shared) definition plus
instance-local state, parameters and optional mix components. Instances need not
have their own file - they can also be created at runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .base import as_str, quantity_map

KNOWN_SECTIONS = {
    "Version",
    "Identity",
    "Id",
    "Name",
    "Definition",
    "BaseMaterial",
    "Material",
    "Variant",
    "Components",
    "State",
    "Parameters",
    "Appearance",
    "Contact",
}


@dataclass
class MixComponent:
    """One component of a material mix (subset of a full instance)."""

    material_ref: str
    concentration: Any = None
    role: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_ref": self.material_ref,
            "concentration": str(self.concentration) if self.concentration is not None else None,
            "role": self.role,
        }


@dataclass
class MaterialInstance:
    instance_id: str
    definition_ref: str
    name: str = ""
    variant: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    components: List[MixComponent] = field(default_factory=list)
    appearance: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None

    def get_state(self, name: str) -> Any:
        return self.state.get(name)

    def get_parameter(self, name: str) -> Any:
        return self.parameters.get(name)

    @classmethod
    def from_sections(cls, sections: Dict[str, Any], source_path: Optional[str] = None) -> "MaterialInstance":
        identity = sections.get("Identity") or {}
        if not isinstance(identity, dict):
            identity = {}
        definition = (
            sections.get("Definition")
            or sections.get("BaseMaterial")
            or sections.get("Material")
            or ""
        )
        if isinstance(definition, dict):
            definition = definition.get("Ref") or definition.get("Definition") or ""

        components_raw = sections.get("Components") or []
        components: List[MixComponent] = []
        for entry in components_raw:
            if isinstance(entry, dict):
                ref = entry.get("MaterialRef") or entry.get("Ref") or ""
                components.append(
                    MixComponent(
                        material_ref=str(ref),
                        concentration=quantity_map({"c": entry.get("Concentration")}).get("c"),
                        role=entry.get("Role"),
                    )
                )

        if not identity.get("Name") and sections.get("Name"):
            identity = {"Name": sections.get("Name")}
        return cls(
            instance_id=as_str(identity.get("Id") or identity.get("Name") or sections.get("Id")),
            definition_ref=as_str(definition),
            name=as_str(identity.get("Name")),
            variant=sections.get("Variant"),
            state=quantity_map(sections.get("State")),
            parameters=quantity_map(sections.get("Parameters")),
            components=components,
            appearance=sections.get("Appearance") if isinstance(sections.get("Appearance"), dict) else None,
            contact=sections.get("Contact") if isinstance(sections.get("Contact"), dict) else None,
            extra={k: v for k, v in sections.items() if k not in KNOWN_SECTIONS},
            source_path=source_path,
        )

    def to_sections(self) -> Dict[str, Any]:
        from .base import scalar_to_primitive

        sections: Dict[str, Any] = {
            "Identity": {"Id": self.instance_id or self.name, "Name": self.name or self.instance_id}
        }
        if self.variant:
            sections["Variant"] = self.variant
        if self.definition_ref:
            sections["Definition"] = self.definition_ref
        if self.components:
            sections["Components"] = [
                {
                    "MaterialRef": c.material_ref,
                    **(
                        {"Concentration": scalar_to_primitive(c.concentration)}
                        if c.concentration is not None
                        else {}
                    ),
                    **({"Role": c.role} if c.role else {}),
                }
                for c in self.components
            ]
        if self.state:
            sections["State"] = {k: scalar_to_primitive(v) for k, v in self.state.items()}
        if self.parameters:
            sections["Parameters"] = {k: scalar_to_primitive(v) for k, v in self.parameters.items()}
        if self.appearance:
            sections["Appearance"] = self.appearance
        if self.contact:
            sections["Contact"] = self.contact
        for key, value in self.extra.items():
            sections[key] = value
        return sections

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "instance",
            "id": self.instance_id,
            "name": self.name,
            "definition_ref": self.definition_ref,
            "variant": self.variant,
            "state": {k: str(v) for k, v in self.state.items()},
            "parameters": {k: str(v) for k, v in self.parameters.items()},
            "components": [c.to_dict() for c in self.components],
            "appearance": self.appearance,
            "contact": self.contact,
            "extra": self.extra,
            "source_path": self.source_path,
        }

    def __repr__(self) -> str:
        return f"MaterialInstance(id={self.instance_id!r} -> {self.definition_ref!r})"
