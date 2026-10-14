"""Runtime integration (Phase 6).

Material assignments in a scene only store a reference to the shared material
definition plus instance parameters. Millions of objects can reference the same
definition; the definition is loaded and cached exactly once. The scene runtime
resolves assignments on demand and reports memory sharing statistics.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .materialsystem import MaterialSystem, ResolvedMaterial
from .model import MaterialInstance, quantity_map
from .resources import ResourceManager


@dataclass
class MaterialAssignment:
    """Binds an object to a shared material definition plus local parameters."""

    object_id: str
    material_ref: str
    instance_id: Optional[str] = None
    state: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {"object": self.object_id, "material": self.material_ref}
        if self.instance_id:
            result["instance"] = self.instance_id
        if self.state:
            result["state"] = {k: str(v) for k, v in self.state.items()}
        if self.parameters:
            result["parameters"] = {k: str(v) for k, v in self.parameters.items()}
        return result


class Scene:
    """A collection of material assignments and their shared instances."""

    def __init__(self, name: str = "scene"):
        self.name = name
        self.instances: Dict[str, MaterialInstance] = {}
        self.assignments: List[MaterialAssignment] = []

    def add_instance(self, instance: MaterialInstance) -> MaterialInstance:
        self.instances[instance.instance_id] = instance
        return instance

    def assign(
        self,
        object_id: str,
        material_ref: str,
        *,
        instance_id: Optional[str] = None,
        state: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> MaterialAssignment:
        assignment = MaterialAssignment(
            object_id=object_id,
            material_ref=material_ref,
            instance_id=instance_id,
            state=dict(state or {}),
            parameters=dict(parameters or {}),
        )
        self.assignments.append(assignment)
        return assignment

    def assignments_for(self, material_ref: str) -> List[MaterialAssignment]:
        return [a for a in self.assignments if a.material_ref == material_ref]

    def shared_material_refs(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for assignment in self.assignments:
            counts[assignment.material_ref] = counts.get(assignment.material_ref, 0) + 1
        return counts

    def sharing_statistics(self) -> Dict[str, Any]:
        counts = self.shared_material_refs()
        total = len(self.assignments)
        unique = len(counts)
        most_shared = max(counts.values()) if counts else 0
        # rough estimate: a shared definition pointer + a small parameter block
        estimated_bytes = total * 32 + unique * 512
        naive_bytes = total * 512
        return {
            "assignments": total,
            "unique_materials": unique,
            "most_shared": most_shared,
            "estimated_bytes": estimated_bytes,
            "naive_duplicate_bytes": naive_bytes,
            "savings": 1.0 - (estimated_bytes / naive_bytes) if naive_bytes else 0.0,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "instances": {k: v.to_dict() for k, v in self.instances.items()},
            "assignments": [a.to_dict() for a in self.assignments],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Scene":
        scene = cls(name=data.get("name", "scene"))
        for instance_data in (data.get("instances") or {}).values():
            instance = MaterialInstance(
                instance_id=instance_data.get("id", ""),
                definition_ref=instance_data.get("definition_ref", ""),
                name=instance_data.get("name", ""),
                variant=instance_data.get("variant"),
                state=quantity_map(instance_data.get("state") or {}),
                parameters=quantity_map(instance_data.get("parameters") or {}),
            )
            scene.add_instance(instance)
        for entry in data.get("assignments") or []:
            scene.assign(
                entry.get("object") or entry.get("object_id") or "",
                entry.get("material") or entry.get("material_ref") or "",
                instance_id=entry.get("instance") or entry.get("instance_id"),
                state=quantity_map(entry.get("state") or {}),
                parameters=quantity_map(entry.get("parameters") or {}),
            )
        return scene


class SceneRuntime:
    """Resolves scene assignments against a material system with caching."""

    def __init__(self, scene: Scene, material_system: Optional[MaterialSystem] = None):
        self.scene = scene
        self.material_system = material_system or MaterialSystem()
        self._resolved: Dict[str, ResolvedMaterial] = {}

    @property
    def manager(self) -> ResourceManager:
        return self.material_system.manager

    def resolve(self, assignment: MaterialAssignment) -> ResolvedMaterial:
        key = assignment.instance_id or f"{assignment.object_id}:{assignment.material_ref}"
        if key in self._resolved:
            return self._resolved[key]
        instance = self.scene.instances.get(assignment.instance_id) if assignment.instance_id else None
        resolved = self.material_system.resolve(
            assignment.material_ref,
            instance=instance,
            state=assignment.state or None,
            parameters=assignment.parameters or None,
        )
        self._resolved[key] = resolved
        return resolved

    def resolve_all(self) -> Dict[str, ResolvedMaterial]:
        return {a.object_id: self.resolve(a) for a in self.scene.assignments}

    async def preload(self, concurrency: int = 8) -> None:
        """Asynchronously preload all referenced material definitions."""
        refs = sorted(self.scene.shared_material_refs().keys())
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def load(ref: str) -> None:
            async with semaphore:
                await self.material_system.manager.aload(ref, "material")

        await asyncio.gather(*(load(ref) for ref in refs))

    def memory_report(self) -> Dict[str, Any]:
        stats = self.scene.sharing_statistics()
        stats["loaded_definitions"] = len(self.manager)
        stats["resolved_instances"] = len(self._resolved)
        return stats
