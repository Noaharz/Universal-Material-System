def test_library_counts(manager):
    atoms = [k for k in manager._by_path if k.startswith("elements/")]
    structures = [k for k in manager._by_path if k.startswith("structures/")]
    materials = [k for k in manager._by_path if k.startswith("materials/")]
    assert len(atoms) == 10
    assert len(structures) == 8
    assert len(materials) == 9


def test_all_materials_resolve(system, manager):
    for path in sorted(manager._by_path):
        if not path.startswith("materials/"):
            continue
        resolved = system.resolve(path)
        assert resolved.definition is not None
        assert resolved.name
        # every referenced structure and atom must resolve
        for structure in resolved.structures:
            assert structure.id


def test_expected_materials_present(manager):
    expected = {
        "water",
        "gold",
        "iron",
        "steel",
        "glass",
        "diamond",
        "concrete",
        "polyethylene",
        "sodium_chloride",
    }
    present = {path.split("/")[-1].split(".")[0] for path in manager._by_path if path.startswith("materials/")}
    assert expected.issubset(present)
