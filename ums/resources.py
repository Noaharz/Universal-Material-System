"""Resource manager: discovery, caching, dependency resolution and versioning.

The resource manager turns logical resource paths (``elements/gold.atom``) and
stable IDs (``element.gold``) into loaded definitions. It caches definitions so
that a shared atom definition is never loaded twice, tracks the dependency graph
(``material -> structure -> atom``), detects cycles and reports missing or
invalid references. Access is thread-safe and an optional asynchronous loader is
provided for engines that stream resources in the background.
"""

from __future__ import annotations

import asyncio
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Union

from .errors import CyclicDependencyError, ParseError, ResourceNotFound
from .model import AtomDefinition, MaterialDefinition, MaterialInstance, StructureDefinition
from .parser import DocumentType, parse_document
from .validation import Validator

Resource = Union[AtomDefinition, StructureDefinition, MaterialDefinition, MaterialInstance]

_SUFFIXES = {".atom", ".structure", ".material", ".instance"}
_KIND_FOR_TYPE = {
    DocumentType.ATOM: "atom",
    DocumentType.STRUCTURE: "structure",
    DocumentType.MATERIAL: "material",
    DocumentType.INSTANCE: "instance",
}


@dataclass
class ResourceReference:
    """A logical reference to another resource."""

    raw: str
    kind: str  # "path" or "id"

    @classmethod
    def parse(cls, raw: str) -> "ResourceReference":
        lowered = raw.lower()
        if lowered.endswith((".atom", ".structure", ".material", ".instance")):
            return cls(raw, "path")
        return cls(raw, "id")

    def __str__(self) -> str:
        return self.raw


def _build_resource(doc_type: DocumentType, sections: dict, path: Optional[str]) -> Resource:
    if doc_type is DocumentType.ATOM:
        return AtomDefinition.from_sections(sections, path)
    if doc_type is DocumentType.STRUCTURE:
        return StructureDefinition.from_sections(sections, path)
    if doc_type is DocumentType.MATERIAL:
        return MaterialDefinition.from_sections(sections, path)
    if doc_type is DocumentType.INSTANCE:
        return MaterialInstance.from_sections(sections, path)
    raise ParseError(f"unsupported document type: {doc_type}")


def _resource_id(resource: Resource) -> str:
    if isinstance(resource, MaterialInstance):
        return resource.instance_id
    return resource.identity.resource_id


class ResourceManager:
    """Load, cache and resolve UMS resources from one or more search paths."""

    def __init__(self, search_paths: Optional[Iterable[Union[str, os.PathLike]]] = None):
        self._paths: List[Path] = []
        self._lock = threading.RLock()
        self._by_id: Dict[str, str] = {}
        self._by_path: Dict[str, str] = {}
        self._cache: Dict[str, Resource] = {}
        self._refs: Dict[str, List[str]] = {}
        self._indexed = False
        for path in search_paths or []:
            self.add_search_path(path)

    # -- discovery ---------------------------------------------------------
    def add_search_path(self, path: Union[str, os.PathLike]) -> None:
        with self._lock:
            candidate = Path(path).expanduser().resolve()
            if candidate not in self._paths:
                self._paths.append(candidate)
            self._indexed = False

    @property
    def search_paths(self) -> List[Path]:
        with self._lock:
            return list(self._paths)

    def index(self, force: bool = False) -> None:
        """Scan all search paths and record resource IDs and logical paths."""
        with self._lock:
            if self._indexed and not force:
                return
            for base in self._paths:
                if not base.is_dir():
                    continue
                for file_path in sorted(base.rglob("*")):
                    if file_path.suffix not in _SUFFIXES or not file_path.is_file():
                        continue
                    try:
                        doc_type, sections = parse_document(
                            file_path.read_text(encoding="utf-8"), str(file_path)
                        )
                        resource = _build_resource(doc_type, sections, str(file_path))
                    except Exception:
                        continue
                    logical = file_path.relative_to(base).as_posix()
                    key = self._register_internal(resource, logical)
            self._indexed = True

    def _register_internal(self, resource: Resource, logical_path: Optional[str] = None) -> str:
        rid = _resource_id(resource)
        stored = resource.source_path or logical_path
        key = stored or rid
        resource.source_path = stored
        self._cache[key] = resource
        if rid:
            self._by_id[rid] = key
        if logical_path:
            self._by_path[logical_path] = key
        return key

    def register(self, resource: Resource, logical_path: Optional[str] = None) -> str:
        """Register an already constructed definition (e.g. created at runtime)."""
        with self._lock:
            return self._register_internal(resource, logical_path)

    # -- resolution --------------------------------------------------------
    def canonical_key(self, ref: str) -> Optional[str]:
        """Return the cache key for a reference, or ``None`` if unknown."""
        self.index()
        with self._lock:
            if ref in self._cache:
                return ref
            if ref in self._by_id:
                return self._by_id[ref]
            if ref in self._by_path:
                return self._by_path[ref]
            reference = ResourceReference.parse(ref)
            if reference.kind == "path":
                for base in self._paths:
                    candidate = base / ref
                    if candidate.is_file():
                        return self._load_file(candidate, ref)
            else:
                for base in self._paths:
                    for suffix in _SUFFIXES:
                        candidate = base / f"{ref}{suffix}"
                        if candidate.is_file():
                            return self._load_file(candidate)
            return None

    def _load_file(self, file_path: Path, logical_path: Optional[str] = None) -> str:
        file_path = Path(file_path)
        key_hint = logical_path or str(file_path)
        with self._lock:
            for base in self._paths:
                try:
                    rel = file_path.relative_to(base).as_posix()
                except ValueError:
                    continue
                if rel in self._by_path:
                    return self._by_path[rel]
            if key_hint in self._cache:
                return key_hint
            text = file_path.read_text(encoding="utf-8")
            doc_type, sections = parse_document(text, str(file_path))
            resource = _build_resource(doc_type, sections, str(file_path))
            logical = logical_path
            if logical is None:
                for base in self._paths:
                    try:
                        logical = file_path.relative_to(base).as_posix()
                        break
                    except ValueError:
                        continue
            return self._register_internal(resource, logical)

    def has(self, ref: str) -> bool:
        return self.canonical_key(ref) is not None

    def __contains__(self, ref: str) -> bool:
        return self.has(ref)

    def get(self, ref: str) -> Optional[Resource]:
        key = self.canonical_key(ref)
        if key is None:
            return None
        with self._lock:
            return self._cache.get(key)

    # -- typed loading -----------------------------------------------------
    def _resolve_or_raise(self, ref: str) -> str:
        key = self.canonical_key(ref)
        if key is None:
            raise ResourceNotFound(f"resource not found: {ref!r} (search paths: {[str(p) for p in self._paths]})")
        return key

    def load(self, ref: str, expected: Optional[str] = None) -> Resource:
        """Load a resource by logical path or ID, raising when it is missing."""
        key = self._resolve_or_raise(ref)
        with self._lock:
            resource = self._cache[key]
        if expected is not None and _kind_of(resource) != expected:
            raise ResourceNotFound(f"resource {ref!r} is a {_kind_of(resource)}, expected a {expected}")
        return resource

    def load_atom(self, ref: str) -> AtomDefinition:
        resource = self.load(ref, expected="atom")
        assert isinstance(resource, AtomDefinition)
        return resource

    def load_structure(self, ref: str) -> StructureDefinition:
        resource = self.load(ref, expected="structure")
        assert isinstance(resource, StructureDefinition)
        return resource

    def load_material(self, ref: str) -> MaterialDefinition:
        resource = self.load(ref, expected="material")
        assert isinstance(resource, MaterialDefinition)
        return resource

    def load_instance(self, ref: str) -> MaterialInstance:
        resource = self.load(ref, expected="instance")
        assert isinstance(resource, MaterialInstance)
        return resource

    def load_definition(self, ref: str) -> Resource:
        """Load a resource without requiring a specific kind."""
        return self.load(ref)

    async def aload(self, ref: str, expected: Optional[str] = None) -> Resource:
        """Asynchronously load a resource using a worker thread."""
        return await asyncio.to_thread(self.load, ref, expected)

    # -- dependencies ------------------------------------------------------
    def dependency_refs(self, resource: Resource) -> List[str]:
        refs: List[str] = []
        if isinstance(resource, StructureDefinition):
            refs.extend(resource.atom_refs())
            for sub in resource.references.get("Substructures", []) or []:
                refs.append(str(sub))
        elif isinstance(resource, MaterialDefinition):
            refs.extend(resource.structure_refs())
            for atom_ref in resource.references.get("AtomDefinitions", []) or []:
                refs.append(str(atom_ref))
        elif isinstance(resource, MaterialInstance):
            if resource.definition_ref:
                refs.append(resource.definition_ref)
            for component in resource.components:
                refs.append(component.material_ref)
        seen: List[str] = []
        for ref in refs:
            if ref and ref not in seen:
                seen.append(ref)
        return seen

    def dependencies(self, ref: str, recursive: bool = True) -> Dict[str, List[str]]:
        """Return the dependency graph rooted at ``ref`` keyed by canonical key."""
        root = self._resolve_or_raise(ref)
        graph: Dict[str, List[str]] = {}
        visiting: List[str] = []
        self._walk(root, graph, visiting, recursive)
        return graph

    def _walk(self, key: str, graph: Dict[str, List[str]], visiting: List[str], recursive: bool) -> None:
        if key in graph:
            return
        if key in visiting:
            cycle = visiting[visiting.index(key):] + [key]
            raise CyclicDependencyError(cycle)
        visiting.append(key)
        with self._lock:
            resource = self._cache[key]
        child_keys: List[str] = []
        for raw in self.dependency_refs(resource):
            child_key = self.canonical_key(raw)
            if child_key is None:
                child_keys.append(raw)
                self._refs.setdefault(key, [])
                if raw not in self._refs[key]:
                    self._refs[key].append(raw)
                continue
            child_keys.append(child_key)
            if recursive:
                self._walk(child_key, graph, visiting, recursive)
        graph[key] = child_keys
        visiting.pop()

    def dependents(self, ref: str) -> List[str]:
        """Return all resources that (transitively) reference ``ref``."""
        target = self._resolve_or_raise(ref)
        result: Set[str] = set()
        with self._lock:
            keys = list(self._cache.keys())
        for key in keys:
            try:
                graph = self.dependencies(key)
            except (ResourceNotFound, CyclicDependencyError):
                continue
            reachable: Set[str] = set()
            stack = [key]
            while stack:
                node = stack.pop()
                for child in graph.get(node, []):
                    if child not in reachable:
                        reachable.add(child)
                        stack.append(child)
            if target in reachable:
                result.add(key)
        result.discard(target)
        return sorted(result)

    def check_cycles(self, ref: Optional[str] = None) -> None:
        """Raise :class:`CyclicDependencyError` if a cycle exists."""
        if ref is not None:
            self.dependencies(ref)
            return
        self.index()
        with self._lock:
            keys = list(self._cache.keys())
        for key in keys:
            try:
                self.dependencies(key)
            except ResourceNotFound:
                continue

    def missing_references(self) -> Dict[str, List[str]]:
        """Return all unresolved references grouped by referring resource."""
        self.index()
        with self._lock:
            keys = list(self._cache.keys())
        missing: Dict[str, List[str]] = {}
        for key in keys:
            with self._lock:
                resource = self._cache[key]
            unresolved = [r for r in self.dependency_refs(resource) if self.canonical_key(r) is None]
            if unresolved:
                missing[key] = unresolved
        return missing

    # -- validation helpers ------------------------------------------------
    def reference_checker(self):
        """Return a callable suitable for :class:`Validator`."""
        return lambda ref: self.has(ref)

    def validate_all(self) -> Dict[str, Any]:
        validator = Validator(reference_checker=self.reference_checker())
        self.index()
        reports: Dict[str, Any] = {}
        with self._lock:
            items = list(self._cache.items())
        for key, resource in items:
            if isinstance(resource, MaterialInstance):
                continue
            reports[key] = validator.validate(resource)
        return reports

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()
            self._by_id.clear()
            self._by_path.clear()
            self._refs.clear()
            self._indexed = False

    def __len__(self) -> int:
        self.index()
        with self._lock:
            return len(self._cache)


def _kind_of(resource: Resource) -> str:
    if isinstance(resource, AtomDefinition):
        return "atom"
    if isinstance(resource, StructureDefinition):
        return "structure"
    if isinstance(resource, MaterialDefinition):
        return "material"
    if isinstance(resource, MaterialInstance):
        return "instance"
    return "unknown"
