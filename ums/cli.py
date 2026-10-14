#!/usr/bin/env python3
"""Command line interface for the Universal Material System.

Examples::

    ums-cli library                        # list all resources
    ums-cli validate library/materials/water.material
    ums-cli deps materials/water.material --library library
    ums-cli resolve materials/water.material --library library --temperature 300 K
    ums-cli solve materials/steel.material --library library --model mechanical --stress 100 MPa
    ums-cli scene examples/scenes/pool_scene.json --library library
    ums-cli fmt library/elements/gold.atom
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .errors import UmsError, CyclicDependencyError
from .model import AtomDefinition, MaterialDefinition, StructureDefinition
from .parser import DocumentType, parse_document
from .resources import ResourceManager, _build_resource, _kind_of
from .serializer import serialize_document
from .units import Quantity, parse_quantity, resolve_unit
from .validation import Severity, Validator


def _default_library() -> Optional[str]:
    env = os.environ.get("UMS_LIBRARY")
    if env:
        return env
    candidate = Path.cwd() / "library"
    if candidate.is_dir():
        return str(candidate)
    return None


def _make_manager(args) -> ResourceManager:
    paths: List[str] = list(getattr(args, "library", None) or [])
    if not paths:
        default = _default_library()
        if default:
            paths.append(default)
    return ResourceManager(paths)


def _parse_value(text: Optional[str]) -> Any:
    if text is None:
        return None
    try:
        return parse_quantity(text)
    except UmsError:
        return text


# -- commands --------------------------------------------------------------
def cmd_library(args) -> int:
    manager = _make_manager(args)
    manager.index()
    counts: Dict[str, int] = {}
    for path in sorted(manager._by_path):
        suffix = Path(path).suffix.lstrip(".")
        counts[suffix] = counts.get(suffix, 0) + 1
    print(f"Search paths: {', '.join(str(p) for p in manager.search_paths) or '(none)'}")
    print(f"Resources:    {len(manager)}")
    for kind, count in sorted(counts.items()):
        print(f"  {kind:<10} {count}")
    if args.kind:
        print("-" * 60)
        for path in sorted(manager._by_path):
            if Path(path).suffix.lstrip(".") == args.kind:
                resource = manager.get(path)
                print(f"  {path:<45} {getattr(resource, 'name', '')}")
    return 0


def cmd_validate(args) -> int:
    manager = _make_manager(args)
    reference_checker = manager.reference_checker() if args.library else None
    validator = Validator(reference_checker=reference_checker)
    status = 0
    for file_path in args.files:
        path = Path(file_path)
        try:
            doc_type, sections = parse_document(path.read_text(encoding="utf-8"), str(path))
            resource = _build_resource(doc_type, sections, str(path))
        except Exception as exc:  # noqa: BLE001 - report parse failure cleanly
            print(f"[PARSE ERROR] {file_path}: {exc}", file=sys.stderr)
            status = 1
            continue
        report = validator.validate(resource)
        label = getattr(resource, "name", "") or getattr(resource, "instance_id", "")
        print(f"{file_path} ({_kind_of(resource)} {label!r})")
        for issue in report.issues:
            marker = {"error": "ERROR", "warning": "WARN", "info": "INFO"}[issue.severity.value]
            print(f"  [{marker}] {issue.code} {issue.path}: {issue.message}")
        print(f"  -> {'VALID' if report.is_valid else 'INVALID'}")
        if not report.is_valid:
            status = 1
    return status


def cmd_fmt(args) -> int:
    path = Path(args.file)
    doc_type, sections = parse_document(path.read_text(encoding="utf-8"), str(path))
    text = serialize_document(doc_type, sections)
    if args.write:
        path.write_text(text, encoding="utf-8")
        print(f"Rewrote {path}")
    else:
        print(text, end="")
    return 0


def cmd_deps(args) -> int:
    manager = _make_manager(args)
    try:
        graph = manager.dependencies(args.ref)
    except CyclicDependencyError as exc:
        print(f"[CYCLE] {exc}", file=sys.stderr)
        return 1
    except UmsError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(graph, indent=2))
        return 0

    def render(key: str, indent: int) -> None:
        resource = manager.get(key)
        label = Path(key).name if key else key
        kind = _kind_of(resource) if resource else "?"
        print(f"{'  ' * indent}{label} ({kind})")
        for child in graph.get(key, []):
            render(child, indent + 1)

    render(manager.canonical_key(args.ref) or args.ref, 0)
    return 0


def cmd_resolve(args) -> int:
    from .materialsystem import MaterialSystem

    manager = _make_manager(args)
    system = MaterialSystem(manager)
    state = {}
    temperature = _parse_value(args.temperature)
    pressure = _parse_value(args.pressure)
    if temperature is not None:
        state["Temperature"] = temperature
    if pressure is not None:
        state["Pressure"] = pressure
    resolved = system.resolve(
        args.ref,
        variant=args.variant,
        profile=args.profile,
        state=state or None,
    )
    print(f"Material: {resolved.name} ({resolved.id})")
    print(f"Category: {resolved.category}")
    print(f"Phase:    {resolved.phase()}")
    print(f"Variant:  {resolved.variant or '-'}   Profile: {resolved.profile or '-'}")
    if resolved.structures:
        print("Structures:")
        for structure in resolved.structures:
            print(f"  - {structure.id} [{structure.structure_type.value}]")
    if resolved.atoms:
        print("Atoms: " + ", ".join(atom.symbol or atom.id for atom in resolved.atoms))
    print("Properties:")
    for name in resolved.definition.properties:
        value = resolved.resolve_property(name)
        if value is not None:
            print(f"  - {name:<24} {value}")
    models = resolved.evaluate_models()
    if models:
        print("Model results:")
        for name, value in models.items():
            print(f"  - {name:<24} {value}")
    return 0


def cmd_solve(args) -> int:
    from .materialsystem import MaterialSystem
    from .science import MechanicalSolver, ThermalSolver

    manager = _make_manager(args)
    system = MaterialSystem(manager)
    state = {}
    temperature = _parse_value(args.temperature)
    if temperature is not None:
        state["Temperature"] = temperature
    resolved = system.resolve(args.ref, state=state or None)
    print(f"Material: {resolved.name} ({resolved.id})")

    if args.model in ("thermal", "all"):
        solver = ThermalSolver.from_material(resolved)
        length = _parse_value(args.length) or Quantity(1.0, resolve_unit("m"))
        hot = _parse_value(args.t_hot) or Quantity(373.15, resolve_unit("K"))
        cold = _parse_value(args.t_cold) or Quantity(293.15, resolve_unit("K"))
        solution = solver.steady_state_1d(length, cold, hot)
        data = solution.to_dict()
        print("[thermal] steady-state 1D Fourier")
        print(f"  heat flux:        {data['heat_flux_W_per_m2']:.3f} W/m^2")
        print(f"  midpoint temp:    {data['midpoint_temperature_K']:.2f} K")
        if data["diffusivity_m2_per_s"]:
            print(f"  thermal diffus.:  {data['diffusivity_m2_per_s']:.4e} m^2/s")

    if args.model in ("mechanical", "all"):
        solver = MechanicalSolver.from_material(resolved)
        stress = _parse_value(args.stress) or Quantity(100.0, resolve_unit("MPa"))
        data = solver.uniaxial(stress).to_dict()
        print("[mechanical] isotropic linear elasticity")
        print(f"  Young's modulus:  {data['youngs_modulus_GPa']:.2f} GPa")
        print(f"  Poisson ratio:    {data['poisson_ratio']:.3f}")
        print(f"  shear modulus:    {data['shear_modulus_GPa']:.2f} GPa")
        print(f"  bulk modulus:     {data['bulk_modulus_GPa']:.2f} GPa")
        print(f"  strain at stress: {data['strain']:.6e}")
    return 0


def cmd_instance(args) -> int:
    from .materialsystem import MaterialSystem

    manager = _make_manager(args)
    path = Path(args.file)
    doc_type, sections = parse_document(path.read_text(encoding="utf-8"), str(path))
    if doc_type is not DocumentType.INSTANCE:
        print(f"[ERROR] {args.file} is not an INSTANCE document", file=sys.stderr)
        return 1
    from .model import MaterialInstance

    instance = MaterialInstance.from_sections(sections, str(path))
    system = MaterialSystem(manager)
    resolved = system.resolve(instance)
    print(f"Instance: {instance.name} ({instance.instance_id})")
    print(f"  -> {resolved.name} ({resolved.id})")
    print(f"  phase: {resolved.phase()}")
    if instance.components:
        print("  components:")
        for component in instance.components:
            print(f"    - {component.material_ref} @ {component.concentration}")
    for name, value in instance.parameters.items():
        print(f"  param {name} = {value}")
    return 0


def cmd_scene(args) -> int:
    from .runtime import Scene, SceneRuntime

    manager = _make_manager(args)
    data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    scene = Scene.from_dict(data)
    runtime = SceneRuntime(scene, _make_system(manager))
    report = runtime.memory_report()
    print(f"Scene: {scene.name}")
    print(f"  assignments:        {report['assignments']}")
    print(f"  unique materials:   {report['unique_materials']}")
    print(f"  most shared:        {report['most_shared']}")
    print(f"  estimated bytes:    {report['estimated_bytes']}")
    print(f"  naive duplicate:    {report['naive_duplicate_bytes']}")
    print(f"  savings:            {report['savings'] * 100:.1f}%")
    if args.resolve:
        resolved = runtime.resolve_all()
        print("  resolved:")
        for object_id, material in resolved.items():
            print(f"    - {object_id:<28} -> {material.name} [{material.phase()}]")
    return 0


def _make_system(manager):
    from .materialsystem import MaterialSystem

    return MaterialSystem(manager)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ums-cli",
        description="Universal Material System CLI (.atom / .structure / .material)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("library", help="List the resource library")
    p.add_argument("--library", "-L", action="append", help="Library search path (repeatable)")
    p.add_argument("--kind", "-k", choices=["atom", "structure", "material", "instance"])
    p.set_defaults(func=cmd_library)

    p = sub.add_parser("validate", help="Parse and validate definition files")
    p.add_argument("files", nargs="+")
    p.add_argument("--library", "-L", action="append")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("fmt", help="Parse and re-serialize a document")
    p.add_argument("file")
    p.add_argument("--write", "-w", action="store_true")
    p.set_defaults(func=cmd_fmt)

    p = sub.add_parser("deps", help="Show the dependency graph of a resource")
    p.add_argument("ref")
    p.add_argument("--library", "-L", action="append")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_deps)

    p = sub.add_parser("resolve", help="Resolve a material and print its properties")
    p.add_argument("ref")
    p.add_argument("--library", "-L", action="append")
    p.add_argument("--variant")
    p.add_argument("--profile")
    p.add_argument("--temperature")
    p.add_argument("--pressure")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("solve", help="Run scientific solvers for a material")
    p.add_argument("ref")
    p.add_argument("--library", "-L", action="append")
    p.add_argument("--model", "-m", choices=["thermal", "mechanical", "all"], default="all")
    p.add_argument("--temperature", default="293 K")
    p.add_argument("--length", default="1 m")
    p.add_argument("--t-hot", dest="t_hot", default="373.15 K")
    p.add_argument("--t-cold", dest="t_cold", default="293.15 K")
    p.add_argument("--stress", default="100 MPa")
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("instance", help="Resolve a material instance file")
    p.add_argument("file")
    p.add_argument("--library", "-L", action="append")
    p.set_defaults(func=cmd_instance)

    p = sub.add_parser("scene", help="Load a scene, report sharing and optionally resolve")
    p.add_argument("file")
    p.add_argument("--library", "-L", action="append")
    p.add_argument("--resolve", action="store_true")
    p.set_defaults(func=cmd_scene)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except UmsError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
