# `.atom` — Atom Definition

An `.atom` file describes an **atomic type / chemical element** — never a
concrete atom at a position in a simulation.

## Sections

### Identity (required)

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `Id` | stable ID | yes | e.g. `element.gold` |
| `Name` | string | yes | e.g. `Gold` |
| `Symbol` | string | recommended | e.g. `Au` |
| `AtomicNumber` | int | recommended | `Z` |

### Version (top level)

`Version: <int>` — starts at `1`.

### Properties (optional)

| Field | Expected dimension | Example |
| --- | --- | --- |
| `AtomicMass` | mass | `196.96657 u` |
| `AtomicRadius` | length | `144 pm` |
| `CovalentRadius` | length | `136 pm` |
| `IonizationEnergy` | energy | `9.226 eV` |
| `Electronegativity` | dimensionless | `2.54` |

### Electronic (optional)

`ElectronConfiguration`, `ValenceElectrons`, further electronic state data.

### Nuclear (optional)

`Isotopes`: a list of `{MassNumber, Abundance, ...}` entries.

### Physical (optional)

Element reference data and further basic physical properties.

### Models (optional)

References to atomic interaction or quantum-mechanical models.

### References (optional)

`DataSource`, `ReferenceIds`, etc.

## Example

```text
ATOM

Version: 1

Identity:
    Id: "element.gold"
    Name: "Gold"
    Symbol: "Au"
    AtomicNumber: 79

Properties:
    AtomicMass: 196.96657 u

Electronic:
    ElectronConfiguration: "[Xe] 4f14 5d10 6s1"

References:
    DataSource: "periodic_table_reference"
```

Missing optional fields do not invalidate the definition.
