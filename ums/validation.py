"""Validation rules for the three UMS resource formats.

Validation is intentionally separated from parsing: parsing answers "is this
syntactically a document?", validation answers "is this a meaningful, consistent
definition?". References to other resources are checked structurally here and
resolved against a library by the :class:`~ums.resources.ResourceManager`.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from .model import AtomDefinition, MaterialDefinition, StructureDefinition
from .model.appearance import ALPHA_MODES, TEXTURE_SLOTS
from .model.contact import COMBINE_MODES
from .units import Quantity

VALID_ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


class Severity(enum.Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Issue:
    code: str
    message: str
    severity: Severity = Severity.ERROR
    path: str = ""

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "path": self.path,
        }


@dataclass
class ValidationReport:
    subject: str = ""
    issues: List[Issue] = field(default_factory=list)

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity is Severity.ERROR]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity is Severity.WARNING]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add(self, code: str, message: str, severity: Severity = Severity.ERROR, path: str = "") -> None:
        self.issues.append(Issue(code, message, severity, path))

    def extend(self, other: "ValidationReport") -> None:
        self.issues.extend(other.issues)

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "valid": self.is_valid,
            "issues": [i.to_dict() for i in self.issues],
        }


ReferenceChecker = Callable[[str], bool]
AssetChecker = Callable[[str], bool]

_APPEARANCE_FIELDS = (
    "BaseColor",
    "Metallic",
    "Roughness",
    "EmissionColor",
    "EmissionStrength",
    "Opacity",
    "AlphaMode",
    "AlphaCutoff",
    "DoubleSided",
    "NormalScale",
    "OcclusionStrength",
)
_APPEARANCE_UNIT_RANGES = {
    "Metallic": (0.0, 1.0),
    "Roughness": (0.0, 1.0),
    "Opacity": (0.0, 1.0),
    "AlphaCutoff": (0.0, 1.0),
    "OcclusionStrength": (0.0, 1.0),
}
_APPEARANCE_LOWER_BOUNDS = {
    "EmissionStrength": 0.0,
    "NormalScale": 0.0,
}
_CONTACT_FIELDS = (
    "StaticFriction",
    "DynamicFriction",
    "Restitution",
    "FrictionCombine",
    "RestitutionCombine",
)
_CONTACT_LOWER_BOUNDS = {
    "StaticFriction": 0.0,
    "DynamicFriction": 0.0,
}
_CONTACT_UNIT_RANGES = {"Restitution": (0.0, 1.0)}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Validator:
    """Validate atom, structure and material definitions.

    ``reference_checker`` is an optional callable returning whether a logical
    UMS resource path can be resolved. ``asset_checker`` is an optional callable
    for opaque, host-owned references (for example texture asset ids): when it is
    set, unresolved ``Appearance`` texture references are errors; otherwise they
    fall back to the ``reference_checker`` and finally to an informational note.
    """

    def __init__(
        self,
        reference_checker: Optional[ReferenceChecker] = None,
        strict_units: bool = True,
        asset_checker: Optional[AssetChecker] = None,
    ):
        self.reference_checker = reference_checker
        self.strict_units = strict_units
        self.asset_checker = asset_checker

    def _check_reference(self, report: ValidationReport, ref: str, path: str) -> None:
        if not ref:
            report.add("REF_EMPTY", "empty resource reference", Severity.ERROR, path)
            return
        if "\\" in ref:
            report.add("REF_BACKSLASH", f"resource path must use '/' not '\\': {ref!r}", Severity.ERROR, path)
        if ref.startswith("/") or (len(ref) > 1 and ref[1] == ":"):
            report.add("REF_ABSOLUTE", f"resource path must be relative: {ref!r}", Severity.ERROR, path)
        if self.reference_checker is not None:
            if not self.reference_checker(ref):
                report.add("REF_UNRESOLVED", f"reference cannot be resolved: {ref!r}", Severity.ERROR, path)
        else:
            report.add("REF_UNCHECKED", f"reference not resolved (no library): {ref!r}", Severity.INFO, path)

    def _check_id(self, report: ValidationReport, resource_id: str, kind: str) -> None:
        if not resource_id:
            report.add("ID_MISSING", f"{kind} Id is required", Severity.ERROR, "Identity.Id")
        elif not VALID_ID_RE.match(resource_id):
            report.add("ID_INVALID", f"{kind} Id has invalid characters: {resource_id!r}", Severity.ERROR, "Identity.Id")

    def validate_atom(self, atom: AtomDefinition) -> ValidationReport:
        report = ValidationReport(subject=atom.id or atom.name or "<atom>")
        self._check_id(report, atom.id, "atom")
        if atom.version < 1:
            report.add("VERSION_INVALID", "version must be >= 1", Severity.ERROR, "Version")
        if not atom.name:
            report.add("NAME_MISSING", "atom Name is required", Severity.WARNING, "Identity.Name")
        if atom.atomic_number is not None and atom.atomic_number <= 0:
            report.add("Z_INVALID", f"AtomicNumber must be positive, got {atom.atomic_number}", Severity.ERROR, "Identity.AtomicNumber")
        self._validate_quantity(report, atom.atomic_mass, "Properties.AtomicMass", _DIM_MASS)
        for key in ("AtomicRadius", "CovalentRadius"):
            self._validate_quantity(report, atom.properties.get(key), f"Properties.{key}", _DIM_LENGTH)
        self._validate_quantity(report, atom.properties.get("IonizationEnergy"), "Properties.IonizationEnergy", _DIM_ENERGY)
        self._validate_quantity(report, atom.properties.get("Electronegativity"), "Properties.Electronegativity", None)
        for ref in atom.references.get("DataSource", []) if isinstance(atom.references.get("DataSource"), list) else [atom.references.get("DataSource")]:
            if ref:
                report.add("REF_EXTERNAL", f"external data source: {ref}", Severity.INFO, "References.DataSource")
        return report

    def validate_structure(self, structure: StructureDefinition) -> ValidationReport:
        report = ValidationReport(subject=structure.id or structure.name or "<structure>")
        self._check_id(report, structure.id, "structure")
        if structure.version < 1:
            report.add("VERSION_INVALID", "version must be >= 1", Severity.ERROR, "Version")
        if structure.structure_type.value == "Custom" and not (structure.crystal or structure.topology):
            report.add(
                "TYPE_AMBIGUOUS",
                "StructureType is Custom or missing but no specific structure sections are present",
                Severity.WARNING,
                "Identity.StructureType",
            )
        atom_ids = []
        for idx, atom in enumerate(structure.atoms):
            if not isinstance(atom, dict):
                report.add("ATOM_ENTRY_INVALID", "topology atom entries must be mappings", Severity.ERROR, f"Topology.Atoms[{idx}]")
                continue
            local_id = atom.get("Id")
            if not local_id:
                report.add("ATOM_LOCAL_ID_MISSING", "topology atom requires a local Id", Severity.ERROR, f"Topology.Atoms[{idx}]")
            elif local_id in atom_ids:
                report.add("ATOM_LOCAL_ID_DUP", f"duplicate topology atom Id: {local_id!r}", Severity.ERROR, f"Topology.Atoms[{idx}]")
            else:
                atom_ids.append(local_id)
            if not atom.get("Type"):
                report.add("ATOM_TYPE_MISSING", f"topology atom {local_id!r} has no Type reference", Severity.ERROR, f"Topology.Atoms[{idx}]")
        for idx, bond in enumerate(structure.bonds):
            if not isinstance(bond, dict):
                report.add("BOND_ENTRY_INVALID", "bond entries must be mappings", Severity.ERROR, f"Topology.Bonds[{idx}]")
                continue
            for endpoint in ("From", "To"):
                value = bond.get(endpoint)
                if not value:
                    report.add("BOND_ENDPOINT_MISSING", f"bond requires {endpoint}", Severity.ERROR, f"Topology.Bonds[{idx}]")
                elif atom_ids and value not in atom_ids:
                    report.add(
                        "BOND_ENDPOINT_UNKNOWN",
                        f"bond endpoint {value!r} is not a declared topology atom",
                        Severity.ERROR,
                        f"Topology.Bonds[{idx}].{endpoint}",
                    )
        for ref in structure.atom_refs():
            self._check_reference(report, ref, "Composition.AtomRef")
        for ref in structure.references.get("Substructures", []) or []:
            self._check_reference(report, str(ref), "References.Substructures")
        if structure.periodicity:
            dims = structure.periodicity.get("Dimensions")
            if dims is not None and not isinstance(dims, int):
                report.add("PERIODICITY_DIMENSIONS", "Periodicity.Dimensions must be an integer", Severity.ERROR, "Periodicity.Dimensions")
            axes = structure.periodicity.get("PeriodicAxes")
            if axes is not None and (not isinstance(axes, list) or not all(isinstance(a, bool) for a in axes)):
                report.add("PERIODICITY_AXES", "PeriodicAxes must be a list of booleans", Severity.ERROR, "Periodicity.PeriodicAxes")
        self._validate_quantity(report, structure.crystal.get("LatticeParameter"), "Crystal.LatticeParameter", _DIM_LENGTH)
        self._validate_quantity(report, structure.geometry.get("BondAngle"), "Geometry.BondAngle", None)
        return report

    def validate_material(self, material: MaterialDefinition) -> ValidationReport:
        report = ValidationReport(subject=material.id or material.name or "<material>")
        self._check_id(report, material.id, "material")
        if material.version < 1:
            report.add("VERSION_INVALID", "version must be >= 1", Severity.ERROR, "Version")
        if not material.name:
            report.add("NAME_MISSING", "material Name is required", Severity.WARNING, "Identity.Name")
        refs = material.structure_refs()
        for ref in refs:
            self._check_reference(report, ref, "Structures")
        for name, value in material.properties.items():
            if isinstance(value, dict):
                model = value.get("Model")
                if not model:
                    report.add("PROPERTY_MODEL_MISSING", f"property {name!r} has a mapping but no Model key", Severity.ERROR, f"Properties.{name}")
        for dim_name, expected in _MATERIAL_DIMENSIONS.items():
            self._validate_quantity(report, material.properties.get(dim_name), f"Properties.{dim_name}", expected)
        for name, profile in material.composition_profiles.items():
            if not profile.composition:
                report.add("PROFILE_EMPTY", f"composition profile {name!r} is empty", Severity.WARNING, f"CompositionProfiles.{name}")
        if material.appearance is not None and material.appearance.present:
            self._validate_appearance(report, material.appearance.to_sections(), "Appearance")
        if material.contact is not None and material.contact.present:
            self._validate_contact(report, material.contact.to_sections(), "Contact")
        if material.contact_pairs:
            self._validate_contact_pairs(
                report, [p.to_sections() for p in material.contact_pairs], "ContactPairs"
            )
        for name, variant in material.variants.items():
            if variant.appearance:
                self._validate_appearance(report, variant.appearance, f"Variants.{name}.Appearance")
            if variant.contact:
                self._validate_contact(report, variant.contact, f"Variants.{name}.Contact")
        if not material.composition and not material.composition_profiles and not refs:
            report.add(
                "COMPOSITION_MISSING",
                "material has neither composition, composition profiles nor structure references",
                Severity.INFO,
                "Composition",
            )
        return report

    def validate(self, obj: Any) -> ValidationReport:
        if isinstance(obj, AtomDefinition):
            return self.validate_atom(obj)
        if isinstance(obj, StructureDefinition):
            return self.validate_structure(obj)
        if isinstance(obj, MaterialDefinition):
            return self.validate_material(obj)
        raise TypeError(f"cannot validate object of type {type(obj).__name__}")

    # -- appearance / contact ---------------------------------------------
    def _validate_color(self, report: ValidationReport, value: Any, path: str, allowed: tuple) -> None:
        if not isinstance(value, list) or len(value) not in allowed:
            report.add("APPEARANCE_LIST", f"{path} must be a list of {' or '.join(map(str, allowed))} numbers",
                       Severity.ERROR, path)
            return
        for component in value:
            if not _is_number(component):
                report.add("APPEARANCE_VALUE", f"{path} must contain numbers", Severity.ERROR, path)
                return
            if component < 0.0 or component > 1.0:
                report.add("APPEARANCE_RANGE", f"{path} components must be between 0 and 1", Severity.ERROR, path)
                return

    def _validate_number(self, report: ValidationReport, value: Any, path: str, lower: Optional[float],
                         upper: Optional[float], code: str) -> None:
        if not _is_number(value):
            report.add(f"{code}_VALUE", f"{path} must be a number", Severity.ERROR, path)
            return
        if lower is not None and value < lower:
            report.add(f"{code}_RANGE", f"{path} must be >= {lower:g}", Severity.ERROR, path)
            return
        if upper is not None and value > upper:
            report.add(f"{code}_RANGE", f"{path} must be <= {upper:g}", Severity.ERROR, path)

    def _validate_texture(self, report: ValidationReport, block: Any, path: str) -> None:
        if not isinstance(block, dict):
            report.add("TEXTURE_INVALID", f"{path} must be a mapping", Severity.ERROR, path)
            return
        ref = block.get("Ref")
        if not isinstance(ref, str) or not ref:
            report.add("TEXTURE_REF_MISSING", f"{path}.Ref is required", Severity.ERROR, path + ".Ref")
        else:
            checker = self.asset_checker or self.reference_checker
            if checker is None:
                report.add("TEXTURE_UNCHECKED", f"{path}.Ref not resolved (no resolver): {ref!r}",
                           Severity.INFO, path + ".Ref")
            elif not checker(ref):
                report.add("TEXTURE_UNRESOLVED", f"{path}.Ref cannot be resolved: {ref!r}",
                           Severity.ERROR, path + ".Ref")
        for uv in ("UVScale", "UVOffset"):
            value = block.get(uv)
            if value is None:
                continue
            if not isinstance(value, list) or len(value) != 2 or not all(_is_number(x) for x in value):
                report.add("TEXTURE_UV", f"{path}.{uv} must be two numbers", Severity.ERROR, path + "." + uv)
        uv_set = block.get("UVSet")
        if uv_set is not None and (isinstance(uv_set, bool) or not isinstance(uv_set, int) or uv_set < 0):
            report.add("TEXTURE_UV", f"{path}.UVSet must be a non-negative integer", Severity.ERROR, path + ".UVSet")

    def _validate_appearance(self, report: ValidationReport, raw: Any, prefix: str) -> None:
        if not isinstance(raw, dict):
            return
        unit_ranges = _APPEARANCE_UNIT_RANGES
        lower_bounds = _APPEARANCE_LOWER_BOUNDS
        for field in _APPEARANCE_FIELDS:
            if field not in raw:
                continue
            value = raw[field]
            path = f"{prefix}.{field}"
            if field == "BaseColor":
                self._validate_color(report, value, path, (3, 4))
            elif field == "EmissionColor":
                self._validate_color(report, value, path, (3,))
            elif field == "AlphaMode":
                if not isinstance(value, str) or value not in ALPHA_MODES:
                    report.add("APPEARANCE_ENUM", f"{path} must be one of {ALPHA_MODES}", Severity.ERROR, path)
            elif field == "DoubleSided":
                if not isinstance(value, bool):
                    report.add("APPEARANCE_VALUE", f"{path} must be a boolean", Severity.ERROR, path)
            elif field in unit_ranges:
                lower, upper = unit_ranges[field]
                self._validate_number(report, value, path, lower, upper, "APPEARANCE")
            else:
                self._validate_number(report, value, path, lower_bounds.get(field), None, "APPEARANCE")
        textures = raw.get("Textures")
        if isinstance(textures, dict):
            for slot in TEXTURE_SLOTS:
                if slot in textures:
                    self._validate_texture(report, textures[slot], f"{prefix}.Textures.{slot}")

    def _validate_contact(self, report: ValidationReport, raw: Any, prefix: str) -> None:
        if not isinstance(raw, dict):
            return
        unit_ranges = _CONTACT_UNIT_RANGES
        lower_bounds = _CONTACT_LOWER_BOUNDS
        for field in _CONTACT_FIELDS:
            if field not in raw:
                continue
            value = raw[field]
            path = f"{prefix}.{field}"
            if field in ("FrictionCombine", "RestitutionCombine"):
                if not isinstance(value, str) or value not in COMBINE_MODES:
                    report.add("CONTACT_ENUM", f"{path} must be one of {COMBINE_MODES}", Severity.ERROR, path)
            elif field in unit_ranges:
                lower, upper = unit_ranges[field]
                self._validate_number(report, value, path, lower, upper, "CONTACT")
            else:
                self._validate_number(report, value, path, lower_bounds.get(field), None, "CONTACT")

    def _validate_contact_pairs(self, report: ValidationReport, raw: Any, prefix: str) -> None:
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            return
        for index, entry in enumerate(raw):
            path = f"{prefix}[{index}]"
            if not isinstance(entry, dict):
                report.add("CONTACT_PAIR_INVALID", f"{path} must be a mapping", Severity.ERROR, path)
                continue
            other = entry.get("Other") or entry.get("Material") or entry.get("Ref")
            if not isinstance(other, str) or not other:
                report.add("CONTACT_PAIR_REF_MISSING", f"{path}.Other is required", Severity.ERROR, path + ".Other")
            elif self.reference_checker is not None and not self.reference_checker(other):
                report.add("CONTACT_PAIR_UNRESOLVED", f"{path}.Other cannot be resolved: {other!r}",
                           Severity.ERROR, path + ".Other")
            if "StaticFriction" in entry:
                self._validate_number(report, entry["StaticFriction"], path + ".StaticFriction", 0.0, None, "CONTACT")
            if "DynamicFriction" in entry:
                self._validate_number(report, entry["DynamicFriction"], path + ".DynamicFriction", 0.0, None, "CONTACT")
            if "Restitution" in entry:
                self._validate_number(report, entry["Restitution"], path + ".Restitution", 0.0, 1.0, "CONTACT")


    def _validate_quantity(self, report: ValidationReport, value: Any, path: str, expected: Optional[tuple]) -> None:
        if value is None:
            return
        if not isinstance(value, Quantity):
            if isinstance(value, dict):
                return  # model reference, validated elsewhere
            report.add("VALUE_NOT_QUANTITY", f"expected a value with unit, got {value!r}", Severity.WARNING, path)
            return
        if expected is not None and value.unit.dimension.exponents != expected:
            report.add(
                "DIMENSION_MISMATCH",
                f"{path} expects {_dimension_name(expected)} but got '{value.unit.symbol}' "
                f"({_dimension_name(value.unit.dimension.exponents)})",
                Severity.ERROR,
                path,
            )


_DIM_MASS = (1, 0, 0, 0, 0, 0, 0)
_DIM_LENGTH = (0, 1, 0, 0, 0, 0, 0)
_DIM_ENERGY = (1, 2, -2, 0, 0, 0, 0)
_DIM_PRESSURE = (1, -1, -2, 0, 0, 0, 0)
_DIM_DENSITY = (1, -3, 0, 0, 0, 0, 0)
_DIM_THERMAL_CONDUCTIVITY = (1, 1, -3, -1, 0, 0, 0)
_DIM_HEAT_CAPACITY = (0, 2, -2, -1, 0, 0, 0)
_DIM_VISCOSITY = (1, -1, -1, 0, 0, 0, 0)
_DIM_ELECTRICAL_CONDUCTIVITY = (-1, -3, 3, 0, 2, 0, 0)

_DIMENSION_NAMES = {
    tuple([0] * 7): "dimensionless",
    _DIM_MASS: "mass",
    _DIM_LENGTH: "length",
    (0, 0, 1, 0, 0, 0, 0): "time",
    (0, 0, 0, 1, 0, 0, 0): "temperature",
    (0, 0, 0, 0, 0, 1, 0): "amount",
    _DIM_ENERGY: "energy",
    _DIM_PRESSURE: "pressure",
    (1, 2, -3, 0, 0, 0, 0): "power",
    _DIM_DENSITY: "density",
    _DIM_THERMAL_CONDUCTIVITY: "thermal conductivity",
    _DIM_HEAT_CAPACITY: "specific heat capacity",
    _DIM_VISCOSITY: "dynamic viscosity",
    _DIM_ELECTRICAL_CONDUCTIVITY: "electrical conductivity",
    (0, 3, 0, 0, 0, 0, 0): "volume",
}


def _dimension_name(exponents: tuple) -> str:
    return _DIMENSION_NAMES.get(tuple(exponents), " * ".join(
        f"{name}^{exp}"
        for name, exp in zip(("mass", "length", "time", "temperature", "current", "amount", "luminosity"), exponents)
        if exp
    ) or "dimensionless")


_MATERIAL_DIMENSIONS = {
    "Density": _DIM_DENSITY,
    "ThermalConductivity": _DIM_THERMAL_CONDUCTIVITY,
    "HeatCapacity": _DIM_HEAT_CAPACITY,
    "Viscosity": _DIM_VISCOSITY,
    "YoungsModulus": _DIM_PRESSURE,
    "ElectricalConductivity": _DIM_ELECTRICAL_CONDUCTIVITY,
}
