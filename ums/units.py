"""Dimensional SI unit and quantity system.

The system uses a 7-dimensional base vector

    [M, L, T, Theta, I, N, J]

for mass, length, time, temperature, electric current, amount of substance and
luminous intensity. Every physical value carries an explicit :class:`Unit`; a
:class:`Quantity` couples a numerical value with a unit and can be converted to
SI base representation for arithmetic.

Compound units such as ``W/(m*K)`` or ``kg/m^3`` are parsed from an expression
grammar so that files never have to rely on hard-coded unit names.
"""

from __future__ import annotations

import math
import re
import threading
from typing import Dict, Tuple

from .errors import UnitError

_BASE_NAMES = ("mass", "length", "time", "temperature", "current", "amount", "luminosity")
_DIM = len(_BASE_NAMES)
_ZERO: Tuple[int, ...] = (0,) * _DIM


class Dimension:
    """A 7-component integer exponent vector over the SI base quantities."""

    __slots__ = ("exponents",)

    def __init__(self, exponents: Tuple[int, ...] = _ZERO):
        exps = tuple(int(e) for e in exponents) if exponents else _ZERO
        if len(exps) != _DIM:
            raise ValueError(f"dimension vector must have {_DIM} components, got {len(exps)}")
        self.exponents = exps

    @classmethod
    def base(cls, index: int) -> "Dimension":
        exps = [0] * _DIM
        exps[index] = 1
        return cls(tuple(exps))

    @property
    def is_dimensionless(self) -> bool:
        return self.exponents == _ZERO

    def __mul__(self, other: "Dimension") -> "Dimension":
        return Dimension(tuple(a + b for a, b in zip(self.exponents, other.exponents)))

    def __truediv__(self, other: "Dimension") -> "Dimension":
        return Dimension(tuple(a - b for a, b in zip(self.exponents, other.exponents)))

    def __pow__(self, power: int) -> "Dimension":
        return Dimension(tuple(a * power for a in self.exponents))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dimension) and self.exponents == other.exponents

    def __hash__(self) -> int:
        return hash(self.exponents)

    def __str__(self) -> str:
        parts = []
        for name, exp in zip(_BASE_NAMES, self.exponents):
            if exp == 0:
                continue
            parts.append(name if exp == 1 else f"{name}^{exp}")
        return " * ".join(parts) if parts else "dimensionless"

    def __repr__(self) -> str:
        return f"Dimension{self.exponents!r}"


DIMENSIONLESS = Dimension()


class Unit:
    """A unit with a symbol, a dimension and a scale factor to SI base units."""

    __slots__ = ("symbol", "dimension", "scale")

    def __init__(self, symbol: str, dimension: Dimension, scale: float = 1.0):
        self.symbol = symbol
        self.dimension = dimension
        self.scale = float(scale)
        if self.scale == 0:
            raise UnitError(f"unit '{symbol}' must have a non-zero scale")

    @property
    def is_dimensionless(self) -> bool:
        return self.dimension.is_dimensionless and math.isclose(self.scale, 1.0)

    def to_si(self, value: float) -> float:
        return value * self.scale

    def from_si(self, value: float) -> float:
        return value / self.scale

    def __mul__(self, other: "Unit") -> "Unit":
        return Unit(f"{self.symbol}*{other.symbol}", self.dimension * other.dimension, self.scale * other.scale)

    def __truediv__(self, other: "Unit") -> "Unit":
        return Unit(f"{self.symbol}/{other.symbol}", self.dimension / other.dimension, self.scale / other.scale)

    def __pow__(self, power: int) -> "Unit":
        return Unit(f"{self.symbol}^{power}", self.dimension ** power, self.scale ** power)

    def compatible(self, other: "Unit") -> bool:
        return self.dimension == other.dimension

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Unit)
            and self.dimension == other.dimension
            and math.isclose(self.scale, other.scale)
        )

    def __hash__(self) -> int:
        return hash((self.symbol, self.dimension))

    def __str__(self) -> str:
        return self.symbol

    def __repr__(self) -> str:
        return f"Unit({self.symbol!r}, {self.dimension}, scale={self.scale})"


class Quantity:
    """A numeric value paired with a unit."""

    __slots__ = ("value", "unit")

    def __init__(self, value: float, unit: Unit | None = None):
        self.value = float(value)
        self.unit = unit if unit is not None else _DIMENSIONLESS

    @property
    def si_value(self) -> float:
        return self.unit.to_si(self.value)

    def to(self, unit: Unit) -> "Quantity":
        if unit.dimension != self.unit.dimension:
            raise UnitError(f"cannot convert '{self.unit}' to '{unit}': incompatible dimensions")
        return Quantity(self.si_value / unit.scale, unit)

    def __add__(self, other: "Quantity") -> "Quantity":
        self._require_same(other)
        return Quantity(self.value + other.to(self.unit).value, self.unit)

    def __sub__(self, other: "Quantity") -> "Quantity":
        self._require_same(other)
        return Quantity(self.value - other.to(self.unit).value, self.unit)

    def __mul__(self, other):
        if isinstance(other, Quantity):
            return Quantity(self.value * other.value, self.unit * other.unit)
        return Quantity(self.value * other, self.unit)

    __rmul__ = __mul__

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            return Quantity(self.value / other.value, self.unit / other.unit)
        return Quantity(self.value / other, self.unit)

    def __neg__(self) -> "Quantity":
        return Quantity(-self.value, self.unit)

    def _require_same(self, other: "Quantity") -> None:
        if not isinstance(other, Quantity):
            raise UnitError(f"expected a Quantity, got {type(other).__name__}")
        if other.unit.dimension != self.unit.dimension:
            raise UnitError(f"incompatible dimensions: {self.unit} vs {other.unit}")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Quantity)
            and math.isclose(self.si_value, other.si_value, rel_tol=1e-9, abs_tol=1e-12)
        )

    def __hash__(self) -> int:
        return hash(round(self.si_value, 12))

    def __str__(self) -> str:
        if self.unit.symbol in ("", "1", "dimensionless"):
            return f"{self.value:g}"
        return f"{self.value:g} {self.unit.symbol}"

    def __repr__(self) -> str:
        return f"Quantity({self.value!r}, {self.unit.symbol!r})"


_DIMENSIONLESS = Unit("", DIMENSIONLESS, 1.0)

_M = Dimension.base(0)
_L = Dimension.base(1)
_T = Dimension.base(2)
_TH = Dimension.base(3)
_I = Dimension.base(4)
_N = Dimension.base(5)
_J = Dimension.base(6)

_ANGLE = DIMENSIONLESS
_RATIO = DIMENSIONLESS


def _dim(*exps: int) -> Dimension:
    return Dimension(tuple(exps))


_BASE_UNITS: Dict[str, Unit] = {
    # mass
    "kg": Unit("kg", _dim(1, 0, 0, 0, 0, 0, 0), 1.0),
    "g": Unit("g", _dim(1, 0, 0, 0, 0, 0, 0), 1e-3),
    "mg": Unit("mg", _dim(1, 0, 0, 0, 0, 0, 0), 1e-6),
    "ug": Unit("ug", _dim(1, 0, 0, 0, 0, 0, 0), 1e-9),
    "t": Unit("t", _dim(1, 0, 0, 0, 0, 0, 0), 1e3),
    "u": Unit("u", _dim(1, 0, 0, 0, 0, 0, 0), 1.66053906660e-27),
    # length
    "m": Unit("m", _dim(0, 1, 0, 0, 0, 0, 0), 1.0),
    "km": Unit("km", _dim(0, 1, 0, 0, 0, 0, 0), 1e3),
    "cm": Unit("cm", _dim(0, 1, 0, 0, 0, 0, 0), 1e-2),
    "mm": Unit("mm", _dim(0, 1, 0, 0, 0, 0, 0), 1e-3),
    "um": Unit("um", _dim(0, 1, 0, 0, 0, 0, 0), 1e-6),
    "nm": Unit("nm", _dim(0, 1, 0, 0, 0, 0, 0), 1e-9),
    "pm": Unit("pm", _dim(0, 1, 0, 0, 0, 0, 0), 1e-12),
    "angstrom": Unit("angstrom", _dim(0, 1, 0, 0, 0, 0, 0), 1e-10),
    "Å": Unit("Å", _dim(0, 1, 0, 0, 0, 0, 0), 1e-10),
    "bohr": Unit("bohr", _dim(0, 1, 0, 0, 0, 0, 0), 5.29177210903e-11),
    # time
    "s": Unit("s", _dim(0, 0, 1, 0, 0, 0, 0), 1.0),
    "ms": Unit("ms", _dim(0, 0, 1, 0, 0, 0, 0), 1e-3),
    "us": Unit("us", _dim(0, 0, 1, 0, 0, 0, 0), 1e-6),
    "ns": Unit("ns", _dim(0, 0, 1, 0, 0, 0, 0), 1e-9),
    "min": Unit("min", _dim(0, 0, 1, 0, 0, 0, 0), 60.0),
    "h": Unit("h", _dim(0, 0, 1, 0, 0, 0, 0), 3600.0),
    # temperature
    "K": Unit("K", _dim(0, 0, 0, 1, 0, 0, 0), 1.0),
    "mK": Unit("mK", _dim(0, 0, 0, 1, 0, 0, 0), 1e-3),
    # electric current
    "A": Unit("A", _dim(0, 0, 0, 0, 1, 0, 0), 1.0),
    "mA": Unit("mA", _dim(0, 0, 0, 0, 1, 0, 0), 1e-3),
    # amount of substance
    "mol": Unit("mol", _dim(0, 0, 0, 0, 0, 1, 0), 1.0),
    "mmol": Unit("mmol", _dim(0, 0, 0, 0, 0, 1, 0), 1e-3),
    # luminous intensity
    "cd": Unit("cd", _dim(0, 0, 0, 0, 0, 0, 1), 1.0),
    # derived
    "N": Unit("N", _dim(1, 1, -2, 0, 0, 0, 0), 1.0),
    "kN": Unit("kN", _dim(1, 1, -2, 0, 0, 0, 0), 1e3),
    "Pa": Unit("Pa", _dim(1, -1, -2, 0, 0, 0, 0), 1.0),
    "hPa": Unit("hPa", _dim(1, -1, -2, 0, 0, 0, 0), 1e2),
    "kPa": Unit("kPa", _dim(1, -1, -2, 0, 0, 0, 0), 1e3),
    "MPa": Unit("MPa", _dim(1, -1, -2, 0, 0, 0, 0), 1e6),
    "GPa": Unit("GPa", _dim(1, -1, -2, 0, 0, 0, 0), 1e9),
    "bar": Unit("bar", _dim(1, -1, -2, 0, 0, 0, 0), 1e5),
    "J": Unit("J", _dim(1, 2, -2, 0, 0, 0, 0), 1.0),
    "kJ": Unit("kJ", _dim(1, 2, -2, 0, 0, 0, 0), 1e3),
    "MJ": Unit("MJ", _dim(1, 2, -2, 0, 0, 0, 0), 1e6),
    "eV": Unit("eV", _dim(1, 2, -2, 0, 0, 0, 0), 1.602176634e-19),
    "W": Unit("W", _dim(1, 2, -3, 0, 0, 0, 0), 1.0),
    "kW": Unit("kW", _dim(1, 2, -3, 0, 0, 0, 0), 1e3),
    "MW": Unit("MW", _dim(1, 2, -3, 0, 0, 0, 0), 1e6),
    "Hz": Unit("Hz", _dim(0, 0, -1, 0, 0, 0, 0), 1.0),
    "C": Unit("C", _dim(0, 0, 1, 0, 1, 0, 0), 1.0),
    "V": Unit("V", _dim(1, 2, -3, 0, -1, 0, 0), 1.0),
    "ohm": Unit("ohm", _dim(1, 2, -3, 0, -2, 0, 0), 1.0),
    "S": Unit("S", _dim(-1, -2, 3, 0, 2, 0, 0), 1.0),
    "F": Unit("F", _dim(-1, -2, 4, 0, 2, 0, 0), 1.0),
    "T": Unit("T", _dim(1, 0, -2, 0, -1, 0, 0), 1.0),
    "Wb": Unit("Wb", _dim(1, 2, -2, 0, -1, 0, 0), 1.0),
    # volume / capacity
    "l": Unit("l", _dim(0, 3, 0, 0, 0, 0, 0), 1e-3),
    "L": Unit("L", _dim(0, 3, 0, 0, 0, 0, 0), 1e-3),
    "mL": Unit("mL", _dim(0, 3, 0, 0, 0, 0, 0), 1e-6),
    # dimensionless ratios and pseudo-units
    "1": Unit("1", DIMENSIONLESS, 1.0),
    "dimensionless": Unit("dimensionless", DIMENSIONLESS, 1.0),
    "%": Unit("%", _RATIO, 0.01),
    "ppm": Unit("ppm", _RATIO, 1e-6),
    "PSU": Unit("PSU", DIMENSIONLESS, 1.0),
    "rad": Unit("rad", _ANGLE, 1.0),
    "deg": Unit("deg", _ANGLE, math.pi / 180.0),
    "rpm": Unit("rpm", _dim(0, 0, -1, 0, 0, 0, 0), 2 * math.pi / 60.0),
}

_ALIASES = {
    "µm": "um",
    "μm": "um",
    "Ohm": "ohm",
    "Ω": "ohm",
    "Å": "angstrom",
}

_lock = threading.RLock()
_registry: Dict[str, Unit] = dict(_BASE_UNITS)
_cache: Dict[str, Unit] = {}


def register_unit(name: str, unit: Unit) -> None:
    """Register (or override) a named unit."""
    with _lock:
        _registry[name] = unit
        _cache.clear()


def get_unit(name: str) -> Unit:
    """Return a named unit or raise :class:`UnitError`."""
    name = _ALIASES.get(name, name)
    with _lock:
        if name in _registry:
            return _registry[name]
    raise UnitError(f"unknown unit: {name!r}")


def known_units() -> Dict[str, Unit]:
    with _lock:
        return dict(_registry)


def resolve_unit(name: str) -> Unit:
    """Resolve a unit name, falling back to parsing compound expressions.

    Unlike :func:`get_unit` this never recurses into :func:`parse_unit` for a
    bare name, so an unknown simple unit still raises a clear error.
    """
    name = _ALIASES.get(name, name)
    with _lock:
        if name in _registry:
            return _registry[name]
    return parse_unit(name)


_NUMBER = r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?"
_NUMBER_RE = re.compile(rf"^{_NUMBER}$")


def parse_quantity(text: str) -> Quantity:
    """Parse a scalar such as ``196.96657 u``, ``104.5 deg`` or ``0.5%``."""
    text = text.strip()
    if text == "":
        raise UnitError("empty quantity")
    if _NUMBER_RE.match(text):
        return Quantity(float(text), _DIMENSIONLESS)
    if text.endswith("%") and _NUMBER_RE.match(text[:-1]):
        return Quantity(float(text[:-1]), get_unit("%"))
    match = re.match(rf"^({_NUMBER})\s+(.+)$", text)
    if match:
        return Quantity(float(match.group(1)), parse_unit(match.group(2)))
    raise UnitError(f"cannot parse quantity: {text!r}")


_TOKEN_RE = re.compile(r"\s*([A-Za-z_ÅµμΩ%]+|\d+\.?\d*|\.\d+|\^|\*|·|×|/|\(|\)|[-+])")


def _tokenize(expr: str) -> list[str]:
    tokens: list[str] = []
    pos = 0
    length = len(expr)
    while pos < length:
        match = _TOKEN_RE.match(expr, pos)
        if not match or match.start() != pos:
            raise UnitError(f"invalid character in unit expression: {expr[pos]!r} in {expr!r}")
        tok = match.group(1)
        if tok == "·" or tok == "×":
            tok = "*"
        if tok.strip() == "":
            pos = match.end()
            continue
        tokens.append(tok)
        pos = match.end()
    return tokens


class _UnitParser:
    def __init__(self, tokens: list[str], expr: str):
        self.tokens = tokens
        self.expr = expr
        self.i = 0

    def _peek(self) -> str | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def _next(self) -> str:
        tok = self._peek()
        if tok is None:
            raise UnitError(f"unexpected end of unit expression: {self.expr!r}")
        self.i += 1
        return tok

    def parse(self) -> Unit:
        unit = self._expr()
        if self.i != len(self.tokens):
            raise UnitError(f"trailing tokens in unit expression: {self.expr!r}")
        return unit

    def _expr(self) -> Unit:
        unit = self._factor()
        while self._peek() in ("*", "/"):
            op = self._next()
            rhs = self._factor()
            unit = unit * rhs if op == "*" else unit / rhs
        return unit

    def _factor(self) -> Unit:
        tok = self._next()
        if tok == "(":
            unit = self._expr()
            if self._next() != ")":
                raise UnitError(f"missing ')' in unit expression: {self.expr!r}")
        elif tok in ("+", "-"):
            unit = self._factor()
        elif _NUMBER_RE.match(tok):
            unit = Unit(tok, DIMENSIONLESS, float(tok))
        else:
            base = get_unit(tok)
            unit = Unit(base.symbol, base.dimension, base.scale)
        if self._peek() == "^":
            self._next()
            sign = 1
            if self._peek() == "-":
                self._next()
                sign = -1
            exp_tok = self._next()
            if not _NUMBER_RE.match(exp_tok) or "." in exp_tok:
                raise UnitError(f"unit exponents must be integers: {exp_tok!r} in {self.expr!r}")
            unit = unit ** (sign * int(exp_tok))
        return unit


def parse_unit(expr: str) -> Unit:
    """Parse a (possibly compound) unit expression such as ``W/(m*K)``."""
    expr = expr.strip()
    if not expr:
        raise UnitError("empty unit expression")
    with _lock:
        if expr in _cache:
            return _cache[expr]
    tokens = _tokenize(expr)
    unit = _UnitParser(tokens, expr).parse()
    with _lock:
        _cache[expr] = unit
    return unit


def unit_from_text(text: str) -> Unit:
    """Return a unit for a textual unit label, falling back to parsing."""
    text = text.strip()
    try:
        return get_unit(text)
    except UnitError:
        return parse_unit(text)


def try_quantity(text: str) -> Quantity | None:
    """Best-effort quantity parsing; returns ``None`` when not a quantity."""
    if not isinstance(text, str):
        if isinstance(text, (int, float)):
            return Quantity(float(text), _DIMENSIONLESS)
        return None
    lowered = text.strip().lower()
    if lowered in ("parameterized", "true", "false"):
        return None
    try:
        return parse_quantity(text)
    except UnitError:
        return None
