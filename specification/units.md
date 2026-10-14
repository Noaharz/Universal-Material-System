# Units and Quantities

Every physical quantity carries an **explicit** unit. Units are never inferred
from the field name.

## 1. Dimensional model

Dimensions are 7-component integer exponent vectors over the SI base quantities:

```
[M, L, T, Theta, I, N, J]
```

| Component | Symbol | Base unit |
| --- | --- | --- |
| mass | M | kg |
| length | L | m |
| time | T | s |
| temperature | Theta | K |
| electric current | I | A |
| amount of substance | N | mol |
| luminous intensity | J | cd |

## 2. Quantity syntax

```
<number> <unit-expression>
```

Examples: `196.96657 u`, `3.567 angstrom`, `104.5 deg`, `0.6 W/(m*K)`,
`293 K`, `101325 Pa`, `35 PSU`, `0.5%`, `4.11e7 S/m`.

A bare number is dimensionless. `%` denotes a ratio with factor `0.01`.

## 3. Unit expressions

Unit expressions combine base and derived units with `*` (or `·`), `/`, `^`
and parentheses:

```
W/(m*K)
kg/m^3
J/(kg*K)
m^2/s
Pa*s
```

## 4. Conversions

Every unit stores a scale factor to SI base representation. Arithmetic on
quantities converts operands to a common unit and rejects incompatible
dimensions. `Quantity.to(unit)` converts only when dimensions match; otherwise a
`UnitError` is raised.

## 5. Registered units

Base: `kg g mg ug t u`, `m km cm mm um nm pm angstrom bohr`, `s ms us ns min h`,
`K mK`, `A mA`, `mol mmol`, `cd`.

Derived: `N kN Pa hPa kPa MPa GPa bar J kJ MJ eV W kW MW Hz C V ohm S F T Wb`.

Volume/capacity: `l L mL`.

Dimensionless/pseudo: `1 dimensionless % ppm PSU rad deg rpm`.

Additional units may be registered at runtime via `register_unit(name, unit)`.
