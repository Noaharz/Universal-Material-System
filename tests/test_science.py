import pytest

from ums.models import available_models, get_model_factory
from ums.science import AtomisticState, MechanicalSolver, MixingModel, ThermalSolver
from ums.units import Quantity, resolve_unit


def test_thermal_steady_state(system):
    resolved = system.resolve("materials/gold.material")
    solver = ThermalSolver.from_material(resolved)
    solution = solver.steady_state_1d(
        Quantity(1.0, resolve_unit("m")),
        Quantity(273.15, resolve_unit("K")),
        Quantity(373.15, resolve_unit("K")),
    )
    # q = k * dT / L = 318 * 100 / 1
    assert solution.heat_flux.value == pytest.approx(31800, rel=1e-6)
    assert solution.temperatures[0] == pytest.approx(273.15)
    assert solution.temperatures[-1] == pytest.approx(373.15)


def test_thermal_transient_runs(system):
    resolved = system.resolve(
        "materials/water.material",
        state={"Temperature": Quantity(300, resolve_unit("K"))},
    )
    solver = ThermalSolver.from_material(resolved)
    solution = solver.transient_1d(
        Quantity(0.1, resolve_unit("m")),
        Quantity(300, resolve_unit("K")),
        Quantity(350, resolve_unit("K")),
        Quantity(350, resolve_unit("K")),
        Quantity(60, resolve_unit("s")),
        n_cells=21,
    )
    assert len(solution.temperatures) == 21
    assert solution.temperatures[0] == pytest.approx(350)
    assert solution.diffusivity is not None


def test_mechanical_isotropic(system):
    resolved = system.resolve("materials/steel.material")
    solver = MechanicalSolver.from_material(resolved)
    shear_gpa = solver.shear_modulus.to(resolve_unit("GPa")).value
    assert shear_gpa == pytest.approx(210 / (2 * 1.29), rel=1e-6)
    solution = solver.uniaxial(Quantity(210, resolve_unit("MPa")))
    assert solution.strain == pytest.approx(1e-3, rel=1e-6)


def test_mixing_models():
    a = Quantity(1000, resolve_unit("kg/m^3"))
    b = Quantity(2000, resolve_unit("kg/m^3"))
    linear = MixingModel("linear").combine([(a, 0.5), (b, 0.5)])
    assert linear.value == pytest.approx(1500)
    harmonic = MixingModel("harmonic").combine([(a, 0.5), (b, 0.5)])
    assert harmonic.value == pytest.approx(1 / (0.5 / 1000 + 0.5 / 2000))


def test_density_from_mass_fractions():
    a = Quantity(1000, resolve_unit("kg/m^3"))
    b = Quantity(2000, resolve_unit("kg/m^3"))
    density = MixingModel.density_from_mass_fractions([(a, 0.5), (b, 0.5)])
    assert density.value == pytest.approx(1 / (0.5 / 1000 + 0.5 / 2000))


def test_atomistic_state_from_structure(manager):
    structure = manager.load_structure("structures/gold_crystal.structure")
    state = AtomisticState.from_structure(structure, repeats=(2, 2, 2))
    assert state.n_atoms == 8
    assert state.box is not None


def test_model_registry():
    names = available_models()
    assert "waterdensity" in names
    factory = get_model_factory("WaterDensity")
    model = factory({"Model": "WaterDensity"})
    q = model.evaluate(state={"Temperature": Quantity(300, resolve_unit("K"))})
    assert 995 < q.value < 998
