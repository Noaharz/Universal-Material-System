"""Computational model registry.

Importing this package registers all built-in property models.
"""

from .base import (
    ModelMetadata,
    PropertyModel,
    StructureModel,
    register_model,
    get_model_factory,
    available_models,
)
from .builtin import (
    ConstantValue,
    TemperaturePolynomial,
    TableInterpolator,
    IdealGasDensity,
    WaterDensity,
    register_builtin_models,
)
from .builtin import _as_quantity

register_builtin_models()

__all__ = [
    "ModelMetadata",
    "PropertyModel",
    "StructureModel",
    "register_model",
    "get_model_factory",
    "available_models",
    "ConstantValue",
    "TemperaturePolynomial",
    "TableInterpolator",
    "IdealGasDensity",
    "WaterDensity",
    "register_builtin_models",
]
