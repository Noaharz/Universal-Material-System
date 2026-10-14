"""Property and structure model interfaces.

A model states which inputs it needs, within which validity range it applies and
with which uncertainty it works - so a simple realtime model and a scientific
model can describe the same material at different fidelity.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..units import Quantity


@dataclass
class ModelMetadata:
    name: str
    domain: str = "generic"
    inputs: List[str] = field(default_factory=list)
    valid_range: Dict[str, tuple] = field(default_factory=dict)
    uncertainty: Optional[float] = None
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "domain": self.domain,
            "inputs": self.inputs,
            "valid_range": {k: list(v) for k, v in self.valid_range.items()},
            "uncertainty": self.uncertainty,
            "description": self.description,
        }


class PropertyModel(ABC):
    """Base class for computational property models."""

    metadata: ModelMetadata

    def __init__(self, metadata: Optional[ModelMetadata] = None):
        if metadata is not None:
            self.metadata = metadata

    @abstractmethod
    def evaluate(
        self,
        *,
        state: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        material: Any = None,
    ) -> Quantity:
        ...

    def __repr__(self) -> str:
        name = getattr(self.metadata, "name", type(self).__name__)
        return f"{type(self).__name__}({name!r})"


class StructureModel(ABC):
    """Base class for structure-related computational models."""

    metadata: ModelMetadata

    @abstractmethod
    def evaluate(self, *, structure: Any, state: Optional[Dict[str, Any]] = None) -> Any:
        ...


_REGISTRY: Dict[str, Callable[..., PropertyModel]] = {}


def register_model(name: str, factory: Callable[..., PropertyModel]) -> None:
    _REGISTRY[name.lower()] = factory


def get_model_factory(name: str) -> Optional[Callable[..., PropertyModel]]:
    return _REGISTRY.get(name.lower())


def available_models() -> List[str]:
    return sorted(_REGISTRY)
