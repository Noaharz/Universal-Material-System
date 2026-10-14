"""The ``.material`` material definition.

A material definition ties together composition, referenced structures,
properties (fixed values or computational models), phases and optional variants
and composition profiles. It describes a reusable material type - never a
concrete object in a scene.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..units import Quantity
from .appearance import Appearance
from .base import Identity, as_str, identity_from_sections, quantity_map
from .contact import Contact, ContactPair, contact_pairs_from_sections, contact_pairs_to_sections

KNOWN_SECTIONS = {
    "Version",
    "Identity",
    "Composition",
    "Structures",
    "Properties",
    "Models",
    "Phases",
    "Variants",
    "CompositionProfiles",
    "References",
    "Appearance",
    "Contact",
    "ContactPairs",
}


@dataclass
class CompositionProfile:
    """A named composition profile (e.g. Pure, Seawater)."""

    name: str
    composition: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "composition": self.composition, "parameters": self.parameters}


@dataclass
class Variant:
    """A named or parameterised modification of a material definition."""

    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)
    appearance: Optional[Dict[str, Any]] = None
    contact: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "overrides": self.overrides,
            "appearance": self.appearance,
            "contact": self.contact,
        }


@dataclass
class MaterialDefinition:
    identity: Identity
    composition: Dict[str, Any] = field(default_factory=dict)
    structures: List[Dict[str, Any]] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    models: Dict[str, Any] = field(default_factory=dict)
    phases: Dict[str, Any] = field(default_factory=dict)
    variants: Dict[str, Variant] = field(default_factory=dict)
    composition_profiles: Dict[str, CompositionProfile] = field(default_factory=dict)
    references: Dict[str, Any] = field(default_factory=dict)
    appearance: Optional[Appearance] = None
    contact: Optional[Contact] = None
    contact_pairs: List[ContactPair] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None

    @property
    def id(self) -> str:
        return self.identity.resource_id

    @property
    def name(self) -> str:
        return self.identity.name

    @property
    def category(self) -> Optional[str]:
        return self.identity.category

    @property
    def version(self) -> int:
        return self.identity.version

    def structure_refs(self) -> List[str]:
        refs: List[str] = []
        for entry in self.structures:
            if isinstance(entry, str):
                refs.append(entry)
            elif isinstance(entry, dict):
                ref = entry.get("StructureRef") or entry.get("Ref") or entry.get("Structure")
                if ref:
                    refs.append(str(ref))
        for ref in self.references.get("Structures", []) or []:
            refs.append(str(ref))
        seen: List[str] = []
        for ref in refs:
            if ref not in seen:
                seen.append(ref)
        return seen

    def get_property(self, name: str) -> Any:
        return self.properties.get(name)

    def get_quantity(self, name: str) -> Optional[Quantity]:
        value = self.properties.get(name)
        return value if isinstance(value, Quantity) else None

    def variant(self, name: str) -> Optional[Variant]:
        return self.variants.get(name)

    def profile(self, name: str) -> Optional[CompositionProfile]:
        return self.composition_profiles.get(name)

    @classmethod
    def from_sections(cls, sections: Dict[str, Any], source_path: Optional[str] = None) -> "MaterialDefinition":
        identity = identity_from_sections(sections)
        identity_section = sections.get("Identity") or {}
        if not isinstance(identity_section, dict):
            identity_section = {}
        if identity.category is None and identity_section.get("Category"):
            identity.category = as_str(identity_section.get("Category"))

        structures_raw = sections.get("Structures") or []
        if isinstance(structures_raw, (str, dict)):
            structures_raw = [structures_raw]
        structures: List[Dict[str, Any]] = []
        for entry in structures_raw:
            if isinstance(entry, str):
                structures.append({"Ref": entry})
            elif isinstance(entry, dict):
                structures.append(entry)

        composition = sections.get("Composition") or {}
        if not isinstance(composition, dict):
            composition = {"Constituents": composition}

        models_raw = sections.get("Models") or {}
        if not isinstance(models_raw, dict):
            models_raw = {}

        composition_profiles: Dict[str, CompositionProfile] = {}
        profiles_raw = sections.get("CompositionProfiles") or {}
        if isinstance(profiles_raw, dict):
            for name, value in profiles_raw.items():
                if isinstance(value, dict):
                    composition_profiles[name] = CompositionProfile(
                        name=name, composition=quantity_map(value)
                    )

        variants: Dict[str, Variant] = {}
        variants_raw = sections.get("Variants") or {}
        if isinstance(variants_raw, dict):
            for name, value in variants_raw.items():
                if isinstance(value, dict):
                    variants[name] = Variant(
                        name=name,
                        parameters=quantity_map(value.get("Parameters") or {}),
                        overrides=quantity_map(value.get("Overrides") or {}),
                        appearance=value.get("Appearance") if isinstance(value.get("Appearance"), dict) else None,
                        contact=value.get("Contact") if isinstance(value.get("Contact"), dict) else None,
                    )
                else:
                    variants[name] = Variant(name=name, parameters=quantity_map({"Value": value}))

        phases: Dict[str, Any] = {}
        phases_raw = sections.get("Phases") or {}
        if isinstance(phases_raw, dict):
            for phase_name, spec in phases_raw.items():
                phases[phase_name] = quantity_map(spec) if isinstance(spec, dict) else spec

        appearance = Appearance.from_sections(sections.get("Appearance")) if "Appearance" in sections else None
        contact = Contact.from_sections(sections.get("Contact")) if "Contact" in sections else None
        contact_pairs = contact_pairs_from_sections(sections.get("ContactPairs"))

        extra = {k: v for k, v in sections.items() if k not in KNOWN_SECTIONS}

        return cls(
            identity=identity,
            composition=composition,
            structures=structures,
            properties=quantity_map(sections.get("Properties")),
            models=models_raw,
            phases=phases,
            variants=variants,
            composition_profiles=composition_profiles,
            references=dict(sections.get("References") or {}),
            appearance=appearance,
            contact=contact,
            contact_pairs=contact_pairs,
            extra=extra,
            source_path=source_path,
        )

    def to_sections(self) -> Dict[str, Any]:
        from .base import scalar_to_primitive

        identity_section: Dict[str, Any] = {"Id": self.id, "Name": self.name}
        if self.category:
            identity_section["Category"] = self.category
        sections: Dict[str, Any] = {"Version": self.version, "Identity": identity_section}
        if self.composition:
            sections["Composition"] = self.composition
        if self.structures:
            sections["Structures"] = self.structures
        if self.properties:
            sections["Properties"] = {k: scalar_to_primitive(v) for k, v in self.properties.items()}
        if self.appearance is not None and self.appearance.present:
            sections["Appearance"] = self.appearance.to_sections()
        if self.contact is not None and self.contact.present:
            sections["Contact"] = self.contact.to_sections()
        if self.contact_pairs:
            sections["ContactPairs"] = contact_pairs_to_sections(self.contact_pairs)
        if self.models:
            sections["Models"] = self.models
        if self.phases:
            sections["Phases"] = self.phases
        if self.composition_profiles:
            sections["CompositionProfiles"] = {
                name: {k: scalar_to_primitive(v) for k, v in profile.composition.items()}
                for name, profile in self.composition_profiles.items()
            }
        if self.variants:
            sections["Variants"] = {
                name: {
                    "Parameters": {k: scalar_to_primitive(v) for k, v in variant.parameters.items()},
                    **({"Overrides": variant.overrides} if variant.overrides else {}),
                    **({"Appearance": variant.appearance} if variant.appearance else {}),
                    **({"Contact": variant.contact} if variant.contact else {}),
                }
                for name, variant in self.variants.items()
            }
        if self.references:
            sections["References"] = self.references
        for key, value in self.extra.items():
            sections[key] = value
        return sections

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "material",
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "composition": self.composition,
            "structures": self.structures,
            "properties": {k: str(v) if isinstance(v, Quantity) else v for k, v in self.properties.items()},
            "models": self.models,
            "phases": self.phases,
            "variants": {k: v.to_dict() for k, v in self.variants.items()},
            "composition_profiles": {k: v.to_dict() for k, v in self.composition_profiles.items()},
            "references": self.references,
            "appearance": self.appearance.to_dict() if self.appearance else None,
            "contact": self.contact.to_dict() if self.contact else None,
            "contact_pairs": [p.to_sections() for p in self.contact_pairs],
            "extra": self.extra,
            "source_path": self.source_path,
        }

    def __repr__(self) -> str:
        return f"MaterialDefinition(id={self.id!r}, name={self.name!r})"
