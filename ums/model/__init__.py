"""Definition models for the Universal Material System."""

from .base import Identity, quantity_map, scalar_to_primitive
from .atom import AtomDefinition
from .structure import StructureDefinition, StructureType
from .material import MaterialDefinition, CompositionProfile, Variant
from .appearance import Appearance, Texture
from .contact import Contact, ContactPair
from .instance import MaterialInstance, MixComponent

__all__ = [
    "Identity",
    "quantity_map",
    "scalar_to_primitive",
    "AtomDefinition",
    "StructureDefinition",
    "StructureType",
    "MaterialDefinition",
    "CompositionProfile",
    "Variant",
    "Appearance",
    "Texture",
    "Contact",
    "ContactPair",
    "MaterialInstance",
    "MixComponent",
]
