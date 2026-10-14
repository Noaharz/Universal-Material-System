import pytest

from ums.units import (
    Dimension,
    Quantity,
    UnitError,
    parse_quantity,
    parse_unit,
    resolve_unit,
)


def test_dimension_arithmetic():
    speed = resolve_unit("m") / resolve_unit("s")
    assert speed.dimension.exponents == (0, 1, -1, 0, 0, 0, 0)
    area = resolve_unit("m") ** 2
    assert area.dimension.exponents == (0, 2, 0, 0, 0, 0, 0)


def test_compound_unit_parsing():
    conductivity = parse_unit("W/(m*K)")
    assert conductivity.dimension.exponents == (1, 1, -3, -1, 0, 0, 0)
    density = parse_unit("kg/m^3")
    assert density.dimension.exponents == (1, -3, 0, 0, 0, 0, 0)


def test_unit_scale_conversion():
    gram = resolve_unit("g")
    assert gram.to_si(1.0) == pytest.approx(1e-3)
    angstrom = resolve_unit("angstrom")
    assert angstrom.to_si(1.0) == pytest.approx(1e-10)


def test_quantity_parsing():
    mass = parse_quantity("196.96657 u")
    assert mass.unit.symbol == "u"
    angle = parse_quantity("104.5 deg")
    assert angle.si_value == pytest.approx(104.5 * 3.14159265 / 180, rel=1e-6)
    ratio = parse_quantity("0.5%")
    assert ratio.si_value == pytest.approx(0.005)
    bare = parse_quantity("2")
    assert bare.unit.is_dimensionless


def test_quantity_arithmetic_and_conversion():
    a = Quantity(1.0, resolve_unit("m"))
    b = Quantity(50.0, resolve_unit("cm"))
    assert (a + b).value == pytest.approx(1.5)
    converted = b.to(resolve_unit("m"))
    assert converted.value == pytest.approx(0.5)


def test_incompatible_dimensions_raise():
    with pytest.raises(UnitError):
        Quantity(1.0, resolve_unit("m")).to(resolve_unit("kg"))
    with pytest.raises(UnitError):
        resolve_unit("not_a_unit")


def test_unknown_unit_error():
    with pytest.raises(UnitError):
        parse_quantity("3.5 flurs")
