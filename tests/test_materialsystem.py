from ums.units import Quantity, resolve_unit


def test_resolve_water_temperature_property(system):
    resolved = system.resolve(
        "materials/water.material",
        state={"Temperature": Quantity(300, resolve_unit("K"))},
    )
    density = resolved.resolve_property("Density")
    assert 995 < density.value < 998


def test_phase_detection(system):
    cold = system.resolve(
        "materials/water.material",
        state={"Temperature": Quantity(250, resolve_unit("K"))},
    )
    hot = system.resolve(
        "materials/water.material",
        state={"Temperature": Quantity(400, resolve_unit("K"))},
    )
    assert cold.phase() == "Solid"
    assert hot.phase() == "Gas"


def test_structures_and_atoms_loaded(system):
    resolved = system.resolve("materials/steel.material")
    structure_ids = {s.id for s in resolved.structures}
    assert "structure.steel_microstructure" in structure_ids
    assert "structure.iron_crystal" in structure_ids
    atom_ids = {a.id for a in resolved.atoms}
    assert "element.iron" in atom_ids
    assert "element.carbon" in atom_ids


def test_variant_and_profile(system):
    resolved = system.resolve(
        "materials/water.material", variant="Seawater", profile="Seawater"
    )
    assert resolved.variant == "Seawater"
    assert resolved.profile == "Seawater"
    assert resolved.composition()["H2O"].value == 96.5
    assert resolved.variant_object().parameters["Salinity"].value == 35


def test_create_instance(system):
    instance = system.create_instance(
        "materials/water.material",
        instance_id="instance.test_pool",
        state={"Temperature": Quantity(293, resolve_unit("K"))},
    )
    resolved = system.resolve(instance)
    assert resolved.instance is instance
    assert resolved.phase() == "Liquid"


def test_unknown_variant_raises(system):
    import pytest

    with pytest.raises(Exception):
        system.resolve("materials/water.material", variant="Nonexistent")
