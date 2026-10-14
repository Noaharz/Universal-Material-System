"""The ``Appearance`` section of a material definition (PBR metallic-roughness).

The section follows the semantics of the glTF 2.0 material model so that
renderers can map it directly. UMS stores only the data - how it is turned into
shaders or GPU state is left to the host.

Only the fields that are actually present are kept, which allows variants and
instances to override a single field (e.g. only ``BaseColor``) and keeps
round-tripping faithful. Missing fields fall back to the documented defaults via
:meth:`Appearance.get`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

TEXTURE_SLOTS = (
    "BaseColor",
    "MetallicRoughness",
    "Normal",
    "Occlusion",
    "Emission",
)

ALPHA_MODES = ("Opaque", "Mask", "Blend")


def _defaults() -> Dict[str, Any]:
    return {
        "BaseColor": [0.8, 0.8, 0.8, 1.0],
        "Metallic": 0.0,
        "Roughness": 0.5,
        "EmissionColor": [0.0, 0.0, 0.0],
        "EmissionStrength": 0.0,
        "Opacity": 1.0,
        "AlphaMode": "Opaque",
        "AlphaCutoff": 0.5,
        "DoubleSided": False,
        "NormalScale": 1.0,
        "OcclusionStrength": 1.0,
    }


@dataclass
class Texture:
    """A texture reference for one appearance slot.

    The ``ref`` is an opaque string. Whether it is a logical UMS path or an
    engine asset id (e.g. a UUID) is decided by the host that resolves it; UMS
    only stores and validates the shape.
    """

    ref: str = ""
    uv_scale: Any = None
    uv_offset: Any = None
    uv_set: Any = None

    @classmethod
    def from_sections(cls, block: Any) -> "Texture":
        if not isinstance(block, dict):
            return cls()
        return cls(
            ref=str(block.get("Ref") or ""),
            uv_scale=block.get("UVScale"),
            uv_offset=block.get("UVOffset"),
            uv_set=block.get("UVSet"),
        )

    def to_sections(self) -> Dict[str, Any]:
        section: Dict[str, Any] = {"Ref": self.ref}
        if self.uv_scale is not None:
            section["UVScale"] = self.uv_scale
        if self.uv_offset is not None:
            section["UVOffset"] = self.uv_offset
        if self.uv_set is not None:
            section["UVSet"] = self.uv_set
        return section


@dataclass
class Appearance:
    """A PBR metallic-roughness appearance block."""

    values: Dict[str, Any] = field(default_factory=dict)
    textures: Dict[str, Any] = field(default_factory=dict)
    present: bool = False

    DEFAULTS = _defaults()

    # -- access ------------------------------------------------------------
    def get(self, name: str, default: Any = None) -> Any:
        if name in self.values:
            return self.values[name]
        if default is not None:
            return default
        return self.DEFAULTS.get(name)

    def has(self, name: str) -> bool:
        return name in self.values

    def texture(self, slot: str) -> Texture:
        return Texture.from_sections(self.textures.get(slot))

    def effective_base_color(self) -> List[float]:
        color = self.get("BaseColor")
        if isinstance(color, list) and color:
            return [float(c) for c in color]
        return list(self.DEFAULTS["BaseColor"])

    def effective_opacity(self) -> float:
        """Opacity derived from a 4-component BaseColor when present."""
        color = self.get("BaseColor")
        if isinstance(color, list) and len(color) == 4:
            return float(color[3])
        return float(self.get("Opacity"))

    # -- construction ------------------------------------------------------
    @classmethod
    def from_sections(cls, section: Any) -> "Appearance":
        if not isinstance(section, dict):
            return cls()
        values: Dict[str, Any] = {}
        textures: Dict[str, Any] = {}
        for key, value in section.items():
            if key == "Textures" and isinstance(value, dict):
                textures = {slot: block for slot, block in value.items()}
            else:
                values[key] = value
        return cls(values=values, textures=textures, present=True)

    def to_sections(self) -> Dict[str, Any]:
        result: Dict[str, Any] = dict(self.values)
        if self.textures:
            result["Textures"] = {slot: block for slot, block in self.textures.items()}
        return result

    # -- composition -------------------------------------------------------
    def merge(self, override: Any) -> "Appearance":
        """Return a new appearance with ``override`` applied on top of this one."""
        if not isinstance(override, dict) or not override:
            return self
        values = dict(self.values)
        textures = {slot: block for slot, block in self.textures.items()}
        for key, value in override.items():
            if key == "Textures" and isinstance(value, dict):
                for slot, block in value.items():
                    textures[slot] = block
            else:
                values[key] = value
        return Appearance(values=values, textures=textures, present=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "present": self.present,
            "values": self.values,
            "textures": self.textures,
        }

    def __bool__(self) -> bool:
        return self.present
