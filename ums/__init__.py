"""Universal Material System (UMS).

A modular architecture for describing real materials across three separate,
reusable resource formats:

    .atom       -> what an atomic type (element) is
    .structure  -> how atoms and other constituents are arranged and bonded
    .material   -> how a material is composed and which properties/models it has

Definitions are decoupled from instances and simulations. A :class:`ResourceManager`
resolves logical resource paths and stable IDs, caches definitions, tracks
dependencies and detects invalid reference cycles.
"""

from .errors import (
    UmsError,
    ParseError,
    ValidationError,
    ReferenceError_,
    ResourceNotFound,
    CyclicDependencyError,
    UnitError,
)
from .units import Dimension, Unit, Quantity, parse_quantity, parse_unit, resolve_unit
from .parser import parse_document, DocumentType
from .model import (
    AtomDefinition,
    StructureDefinition,
    MaterialDefinition,
    MaterialInstance,
    CompositionProfile,
    Variant,
)
from .validation import Validator, ValidationReport, Issue
from .resources import ResourceManager, ResourceReference
from .materialsystem import MaterialSystem, ResolvedMaterial
from .runtime import Scene, MaterialAssignment, SceneRuntime
from .science import ThermalSolver, MechanicalSolver, MixingModel, AtomisticState
from . import models

__version__ = "2.0.0"

__all__ = [
    "UmsError",
    "ParseError",
    "ValidationError",
    "ReferenceError_",
    "ResourceNotFound",
    "CyclicDependencyError",
    "UnitError",
    "Dimension",
    "Unit",
    "Quantity",
    "parse_quantity",
    "parse_unit",
    "resolve_unit",
    "parse_document",
    "DocumentType",
    "AtomDefinition",
    "StructureDefinition",
    "MaterialDefinition",
    "MaterialInstance",
    "CompositionProfile",
    "Variant",
    "Validator",
    "ValidationReport",
    "Issue",
    "ResourceManager",
    "ResourceReference",
    "MaterialSystem",
    "ResolvedMaterial",
    "Scene",
    "MaterialAssignment",
    "SceneRuntime",
    "ThermalSolver",
    "MechanicalSolver",
    "MixingModel",
    "AtomisticState",
    "models",
    "__version__",
]
