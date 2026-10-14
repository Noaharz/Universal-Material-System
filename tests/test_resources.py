import pytest

from ums.errors import CyclicDependencyError, ResourceNotFound
from ums.resources import ResourceManager


def test_index_and_lookup(manager):
    assert len(manager) == 42
    assert manager.has("elements/gold.atom")
    assert manager.has("element.gold")
    assert manager.get("element.gold").symbol == "Au"
    assert not manager.has("elements/unobtainium.atom")


def test_load_typed(manager):
    atom = manager.load_atom("element.hydrogen")
    assert atom.symbol == "H"
    material = manager.load_material("materials/water.material")
    assert material.name == "Water"
    with pytest.raises(ResourceNotFound):
        manager.load_structure("materials/water.material")


def test_caching_returns_same_object(manager):
    a = manager.load_atom("elements/hydrogen.atom")
    b = manager.load_atom("element.hydrogen")
    assert a is b


def test_dependency_graph(manager):
    graph = manager.dependencies("materials/water.material")
    assert len(graph) == 4  # material + structure + 2 atoms
    keys = list(graph)
    assert any(k.endswith("water.structure") for k in keys)


def test_dependents(manager):
    dependents = manager.dependents("elements/hydrogen.atom")
    assert any(d.endswith("water.structure") for d in dependents)
    assert any(d.endswith("water.material") for d in dependents)
    assert any(d.endswith("polyethylene.material") for d in dependents)


def test_missing_references_none(manager):
    assert manager.missing_references() == {}


def test_missing_reference_reported(tmp_path):
    (tmp_path / "elements").mkdir()
    (tmp_path / "materials").mkdir()
    (tmp_path / "elements" / "x.atom").write_text('ATOM\n\nVersion: 1\n\nIdentity:\n    Id: "element.x"\n    Name: "X"\n')
    (tmp_path / "materials" / "broken.material").write_text(
        'MATERIAL\n\nVersion: 1\n\nIdentity:\n    Id: "material.broken"\n    Name: "Broken"\n\n'
        'Structures:\n    - Ref: "structures/missing.structure"\n'
    )
    manager = ResourceManager([tmp_path])
    missing = manager.missing_references()
    assert any("materials/broken.material" in k for k in missing)


def test_cycle_detection(tmp_path):
    (tmp_path / "structures").mkdir()
    (tmp_path / "elements").mkdir()
    (tmp_path / "elements" / "c.atom").write_text('ATOM\n\nVersion: 1\n\nIdentity:\n    Id: "element.c"\n    Name: "C"\n')
    (tmp_path / "structures" / "a.structure").write_text(
        'STRUCTURE\n\nVersion: 1\n\nIdentity:\n    Id: "structure.a"\n    Name: "A"\n    StructureType: Custom\n\n'
        'References:\n    Substructures:\n        - "structures/b.structure"\n'
    )
    (tmp_path / "structures" / "b.structure").write_text(
        'STRUCTURE\n\nVersion: 1\n\nIdentity:\n    Id: "structure.b"\n    Name: "B"\n    StructureType: Custom\n\n'
        'References:\n    Substructures:\n        - "structures/a.structure"\n'
    )
    manager = ResourceManager([tmp_path])
    with pytest.raises(CyclicDependencyError):
        manager.dependencies("structures/a.structure")


def test_validation_of_whole_library(manager):
    reports = manager.validate_all()
    invalid = {k: r for k, r in reports.items() if not r.is_valid}
    assert not invalid, {k: [i.message for i in r.errors] for k, r in invalid.items()}
