"""Built-in property models shipped with the Universal Material System."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from ..errors import UmsError
from ..units import Quantity, resolve_unit, parse_quantity
from .base import ModelMetadata, PropertyModel, register_model

R_GAS = 8.314462618  # J/(mol*K)


def _lookup(mapping: Optional[Dict[str, Any]], *names: str) -> Any:
    if not mapping:
        return None
    for name in names:
        if name in mapping:
            return mapping[name]
    lowered = {str(k).lower(): v for k, v in mapping.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _temperature_kelvin(state: Optional[Dict[str, Any]]) -> float:
    value = _lookup(state, "Temperature", "T")
    if value is None:
        raise UmsError("model requires a state Temperature")
    if isinstance(value, Quantity):
        return value.to(resolve_unit("K")).value
    return float(value)


def _pressure_pascal(state: Optional[Dict[str, Any]]) -> float:
    value = _lookup(state, "Pressure", "p", "P")
    if value is None:
        raise UmsError("model requires a state Pressure")
    if isinstance(value, Quantity):
        return value.to(resolve_unit("Pa")).value
    return float(value)


class ConstantValue(PropertyModel):
    """A property that does not depend on state."""

    def __init__(self, value: Quantity):
        self.value = value
        self.metadata = ModelMetadata(name="Constant", inputs=[], description="Fixed property value")

    def evaluate(self, *, state=None, parameters=None, material=None) -> Quantity:
        return self.value


class TemperaturePolynomial(PropertyModel):
    """Polynomial in absolute temperature: sum(coeff[i] * T^i)."""

    def __init__(self, coefficients: List[Quantity], name: str = "TemperaturePolynomial"):
        if not coefficients:
            raise UmsError("TemperaturePolynomial needs at least one coefficient")
        self.coefficients = coefficients
        self.metadata = ModelMetadata(
            name=name,
            domain="thermal",
            inputs=["Temperature"],
            description="Polynomial dependence on temperature",
        )

    def evaluate(self, *, state=None, parameters=None, material=None) -> Quantity:
        t = _temperature_kelvin(state)
        unit = self.coefficients[0].unit
        acc = self.coefficients[0].value
        for order, coeff in enumerate(self.coefficients[1:], start=1):
            acc += coeff.to(unit).value * (t ** order)
        return Quantity(acc, unit)


class TableInterpolator(PropertyModel):
    """Linear interpolation of a property from tabulated (x, value) points."""

    def __init__(self, points: List[Dict[str, Any]], x_key: str = "Temperature", name: str = "TableInterpolator"):
        self.points = []
        for point in points:
            x = point.get(x_key) or point.get("x")
            y = point.get("Value") or point.get("value") or point.get("y")
            self.points.append((_as_float(x), _as_quantity(y)))
        self.points.sort(key=lambda p: p[0])
        self.metadata = ModelMetadata(
            name=name,
            domain="generic",
            inputs=[x_key],
            description=f"Linear interpolation from {len(self.points)} tabulated points",
        )

    def evaluate(self, *, state=None, parameters=None, material=None) -> Quantity:
        if not self.points:
            raise UmsError("TableInterpolator has no data points")
        x = None
        if state:
            for key in ("Temperature", "Pressure"):
                if key in state:
                    value = state[key]
                    x = value.si_value if isinstance(value, Quantity) else float(value)
                    break
        if x is None:
            x = self.points[0][0]
        if x <= self.points[0][0]:
            return self.points[0][1]
        if x >= self.points[-1][0]:
            return self.points[-1][1]
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:]):
            if x0 <= x <= x1:
                ratio = (x - x0) / (x1 - x0) if x1 != x0 else 0.0
                return y0 + (y1 - y0) * ratio
        return self.points[-1][1]


class IdealGasDensity(PropertyModel):
    """Density of an ideal gas: rho = p * M / (R * T)."""

    def __init__(self, molar_mass: Optional[Quantity] = None, name: str = "IdealGasDensity"):
        self.molar_mass = molar_mass
        self.metadata = ModelMetadata(
            name=name,
            domain="thermal",
            inputs=["Temperature", "Pressure"],
            description="Ideal gas law density",
        )

    def evaluate(self, *, state=None, parameters=None, material=None) -> Quantity:
        molar_mass = self.molar_mass
        if molar_mass is None and parameters and "MolarMass" in parameters:
            molar_mass = parameters["MolarMass"]
        if molar_mass is None:
            raise UmsError("IdealGasDensity requires a MolarMass")
        t = _temperature_kelvin(state)
        p = _pressure_pascal(state)
        m_kg_per_mol = molar_mass.to(resolve_unit("kg")).value
        rho = p * m_kg_per_mol / (R_GAS * t)
        return Quantity(rho, resolve_unit("kg/m^3"))


class WaterDensity(PropertyModel):
    """Density of liquid water as a function of temperature.

    Uses the standard pure-water density polynomial (temperature in degrees
    Celsius), valid for roughly 0-100 C at 1 atm.
    """

    _COEFFS = (999.842594, 6.793952e-2, -9.095290e-3, 1.001685e-4, -1.120083e-6, 6.536332e-9)

    def __init__(self, name: str = "WaterDensity"):
        self.metadata = ModelMetadata(
            name=name,
            domain="thermal",
            inputs=["Temperature"],
            valid_range={"Temperature": (273.15, 373.15)},
            uncertainty=0.001,
            description="Liquid water density vs. temperature near 1 atm",
        )

    def evaluate(self, *, state=None, parameters=None, material=None) -> Quantity:
        t_kelvin = _temperature_kelvin(state)
        t = t_kelvin - 273.15
        rho = 0.0
        for power, coeff in enumerate(self._COEFFS):
            rho += coeff * (t ** power)
        return Quantity(rho, resolve_unit("kg/m^3"))


def _as_float(value: Any) -> float:
    if isinstance(value, Quantity):
        return value.si_value
    return float(value)


def _as_quantity(value: Any) -> Quantity:
    if isinstance(value, Quantity):
        return value
    if isinstance(value, (int, float)):
        return Quantity(float(value))
    return parse_quantity(str(value))


def _factory(cls, key: str = "Model"):
    def factory(config: Dict[str, Any]) -> PropertyModel:
        kwargs = {k: v for k, v in config.items() if k not in (key, "Parameters")}
        params = config.get("Parameters") or {}
        kwargs.update(params)
        if cls is ConstantValue:
            value = kwargs.get("Value") or kwargs.get("value")
            return ConstantValue(_as_quantity(value))
        if cls is TemperaturePolynomial:
            coeffs = kwargs.get("Coefficients") or kwargs.get("coefficients") or []
            return TemperaturePolynomial([_as_quantity(c) for c in coeffs], name=config.get("Model", "TemperaturePolynomial"))
        if cls is TableInterpolator:
            return TableInterpolator(kwargs.get("Points") or kwargs.get("points") or [])
        if cls is IdealGasDensity:
            mm = kwargs.get("MolarMass")
            return IdealGasDensity(_as_quantity(mm) if mm is not None else None)
        return cls()

    return factory


def register_builtin_models() -> None:
    register_model("Constant", _factory(ConstantValue))
    register_model("TemperaturePolynomial", _factory(TemperaturePolynomial))
    register_model("TableInterpolator", _factory(TableInterpolator))
    register_model("IdealGasDensity", _factory(IdealGasDensity))
    register_model("WaterDensity", _factory(WaterDensity))
