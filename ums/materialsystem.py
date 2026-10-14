"""The materialsystem (Phase 4).

Ties the resource manager to resolved, usable materials: composition, referenced
structures, properties (fixed values or computational models), parameters,
variants and composition profiles. Model implementations live in
:mod:`ums.models`; the materialsystem only decides *which* model is used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .errors import UmsError
from .models import get_model_factory
from .model import (
    AtomDefinition,
    CompositionProfile,
    MaterialDefinition,
    MaterialInstance,
    StructureDefinition,
    Variant,
)
from .resources import ResourceManager
from .units import Quantity, get_unit, parse_quantity


@dataclass
class ResolvedMaterial:
    """A material definition with a concrete variant/profile/state/parameters."""

    definition: MaterialDefinition
    instance: Optional[MaterialInstance] = None
    variant: Optional[str] = None
    profile: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    structures: List[StructureDefinition] = field(default_factory=list)
    atoms: List[AtomDefinition] = field(default_factory=list)
    _cache: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def category(self) -> Optional[str]:
        return self.definition.category

    def structure_for_role(self, role: str) -> Optional[StructureDefinition]:
        for entry in self.definition.structures:
            if isinstance(entry, dict) and str(entry.get("Role", "")).lower() == role.lower():
                ref = entry.get("Ref") or entry.get("StructureRef")
                return next((s for s in self.structures if s.id == ref or s.source_path == ref), None)
        return None

    def composition(self) -> Dict[str, Any]:
        if self.profile and self.profile in self.definition.composition_profiles:
            return dict(self.definition.composition_profiles[self.profile].composition)
        return dict(self.definition.composition)

    def variant_object(self) -> Optional[Variant]:
        if self.variant:
            return self.definition.variant(self.variant)
        return None

    def resolve_property(self, name: str) -> Optional[Quantity]:
        """Resolve a property to a quantity, evaluating a model when referenced."""
        if name in self._cache:
            return self._cache[name]
        value = self._apply_overrides(name)
        if value is None:
            return None
        quantity = self._evaluate_value(value)
        if quantity is not None:
            self._cache[name] = quantity
        return quantity

    def _apply_overrides(self, name: str) -> Any:
        value = self.definition.properties.get(name)
        variant = self.variant_object()
        if variant and name in variant.parameters:
            value = variant.parameters[name]
        if variant and name in variant.overrides:
            value = variant.overrides[name]
        return value

    def _evaluate_value(self, value: Any) -> Optional[Quantity]:
        if isinstance(value, Quantity):
            return value
        if isinstance(value, dict):
            model_name = value.get("Model")
            if not model_name:
                return None
            factory = get_model_factory(model_name)
            if factory is None:
                raise UmsError(f"unknown property model: {model_name!r}")
            model = factory(value)
            return model.evaluate(state=self.state, parameters=self.parameters, material=self.definition)
        if isinstance(value, str):
            try:
                return parse_quantity(value)
            except Exception:
                return None
        if isinstance(value, (int, float)):
            return Quantity(float(value))
        return None

    def evaluate_models(self) -> Dict[str, Quantity]:
        """Evaluate every model-backed property and return the results."""
        results: Dict[str, Quantity] = {}
        for name, value in self.definition.properties.items():
            if isinstance(value, dict) and value.get("Model"):
                result = self.resolve_property(name)
                if result is not None:
                    results[name] = result
        return results

    def phase(self) -> str:
        """Best-effort phase from declared phase temperature ranges."""
        temperature = self.state.get("Temperature")
        if isinstance(temperature, Quantity):
            t = temperature.to(get_unit("K")).value
        elif temperature is not None:
            t = float(temperature)
        else:
            t = None
        phases = self.definition.phases or {}
        for phase_name, spec in phases.items():
            if not isinstance(spec, dict):
                continue
            lower = _as_kelvin(spec.get("Min") or spec.get("Lower"))
            upper = _as_kelvin(spec.get("Max") or spec.get("Upper"))
            if t is None:
                continue
            if (lower is None or t >= lower) and (upper is None or t < upper):
                return phase_name
        # infer from melting/boiling if present
        melting = self._temperature("MeltingPoint")
        boiling = self._temperature("BoilingPoint")
        if t is not None:
            if melting is not None and t < melting:
                return "Solid"
            if boiling is not None and t >= boiling:
                return "Gas"
            if melting is not None:
                return "Liquid"
        return phases and next(iter(phases)) or "Unknown"

    def _temperature(self, name: str) -> Optional[float]:
        value = self.definition.properties.get(name)
        if isinstance(value, Quantity):
            return value.to(get_unit("K")).value
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material": self.definition.id,
            "name": self.definition.name,
            "variant": self.variant,
            "profile": self.profile,
            "state": {k: str(v) for k, v in self.state.items()},
            "parameters": {k: str(v) for k, v in self.parameters.items()},
            "phase": self.phase(),
            "structures": [s.id for s in self.structures],
            "atoms": [a.id for a in self.atoms],
        }


class MaterialSystem:
    """High-level API for resolving materials, instances and mixes."""

    def __init__(self, manager: Optional[ResourceManager] = None):
        self.manager = manager if manager is not None else ResourceManager()

    def resolve(
        self,
        material: Any,
        *,
        variant: Optional[str] = None,
        profile: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        instance: Optional[MaterialInstance] = None,
    ) -> ResolvedMaterial:
        if isinstance(material, MaterialDefinition):
            definition = material
        elif isinstance(material, MaterialInstance):
            instance = material
            definition = self.manager.load_material(material.definition_ref)
        else:
            definition = self.manager.load_material(str(material))

        merged_state = dict(state or {})
        merged_params = dict(parameters or {})
        if instance is not None:
            merged_state = {**instance.state, **merged_state}
            merged_params = {**instance.parameters, **merged_params}
            variant = variant or instance.variant
        if variant is not None and definition.variant(variant) is None:
            raise UmsError(f"material {definition.id!r} has no variant {variant!r}")

        structures: List[StructureDefinition] = []
        atoms: List[AtomDefinition] = []
        for ref in definition.structure_refs():
            structure = self.manager.load_structure(ref)
            structures.append(structure)
            for atom_ref in structure.atom_refs():
                atom = self.manager.load_atom(atom_ref)
                if all(a.id != atom.id for a in atoms):
                    atoms.append(atom)

        return ResolvedMaterial(
            definition=definition,
            instance=instance,
            variant=variant,
            profile=profile,
            state=merged_state,
            parameters=merged_params,
            structures=structures,
            atoms=atoms,
        )

    def create_instance(
        self,
        material_ref: str,
        instance_id: Optional[str] = None,
        *,
        name: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        variant: Optional[str] = None,
        components: Optional[List[Any]] = None,
        register: bool = True,
    ) -> MaterialInstance:
        definition = self.manager.load_material(material_ref)
        instance = MaterialInstance(
            instance_id=instance_id or f"{definition.id}#instance",
            definition_ref=material_ref,
            name=name or instance_id or definition.name,
            variant=variant,
            state=dict(state or {}),
            parameters=dict(parameters or {}),
            components=list(components or []),
        )
        if register:
            self.manager.register(instance)
        return instance

    def resolve_mix(self, instance: MaterialInstance) -> ResolvedMaterial:
        """Resolve a base material mixed with additional components."""
        resolved = self.resolve(instance)
        return resolved

    def profile_names(self, material: Any) -> List[str]:
        definition = material if isinstance(material, MaterialDefinition) else self.manager.load_material(str(material))
        return list(definition.composition_profiles.keys())

    def variant_names(self, material: Any) -> List[str]:
        definition = material if isinstance(material, MaterialDefinition) else self.manager.load_material(str(material))
        return list(definition.variants.keys())


def _as_kelvin(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Quantity):
        return value.to(get_unit("K")).value
    return float(value)
