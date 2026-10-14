# Validation Rules

Validation is separate from parsing. Errors should be reported on import/load,
not during a simulation. Missing optional data is distinguishable from invalid
required data.

## `.atom`

* Valid atom ID (present, no illegal characters)
* Valid element identity
* Permissible property values
* Correct units (dimensional checks)
* Unique version declaration (`>= 1`)

## `.structure`

* Valid structure type
* Resolvable references
* Unique local IDs
* Valid bonds (endpoints must be declared atoms)
* Consistent geometry data
* Valid periodicity when used

## `.material`

* Valid material ID
* Consistent composition
* Resolvable structure and model references
* Valid property definitions
* Unique units
* Valid variant parameters

## Severities

| Severity | Meaning |
| --- | --- |
| `error` | Definition is invalid; `report.is_valid` becomes `False` |
| `warning` | Suspicious but not fatal (e.g. missing name) |
| `info` | Neutral note (e.g. unresolved reference when no library is attached) |

## Reference checking

`Validator(reference_checker=...)` turns unresolved references into errors. The
resource manager provides a ready-made checker via `reference_checker()`.
