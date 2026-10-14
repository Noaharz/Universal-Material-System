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
* Valid `Appearance` (PBR ranges, alpha mode, texture shape)
* Valid `Contact` (friction/restitution ranges, combine enums) and `ContactPairs`

A material without chemistry (no composition, profiles or structure references)
is still valid; it is reported as `info` (`COMPOSITION_MISSING`).

### Appearance and Contact codes

| Code | Severity | Meaning |
| --- | --- | --- |
| `APPEARANCE_LIST` | error | a colour is not a list of the wrong length (3 or 4 for `BaseColor`, 3 for `EmissionColor`) |
| `APPEARANCE_VALUE` | error | a field has the wrong type (e.g. non-numeric, non-boolean) |
| `APPEARANCE_RANGE` | error | a value is outside its allowed range (`[0, 1]` or `>= 0`) |
| `APPEARANCE_ENUM` | error | `AlphaMode` is not `Opaque`, `Mask` or `Blend` |
| `TEXTURE_INVALID` | error | a texture slot is not a mapping |
| `TEXTURE_REF_MISSING` | error | a texture slot has no `Ref` |
| `TEXTURE_UNRESOLVED` | error | the texture `Ref` could not be resolved by the host checker |
| `TEXTURE_UNCHECKED` | info | the texture `Ref` is opaque and no checker is attached |
| `TEXTURE_UV` | error | `UVScale`/`UVOffset` are not two numbers or `UVSet` is not a non-negative integer |
| `CONTACT_VALUE` | error | a contact field has the wrong type |
| `CONTACT_RANGE` | error | friction is negative or restitution is outside `[0, 1]` |
| `CONTACT_ENUM` | error | a combine rule is not a known mode |
| `CONTACT_PAIR_INVALID` | error | a `ContactPairs` entry is not a mapping |
| `CONTACT_PAIR_REF_MISSING` | error | a `ContactPairs` entry has no `Other` |
| `CONTACT_PAIR_UNRESOLVED` | error | `Other` cannot be resolved by the reference checker |

## Severities

| Severity | Meaning |
| --- | --- |
| `error` | Definition is invalid; `report.is_valid` becomes `False` |
| `warning` | Suspicious but not fatal (e.g. missing name) |
| `info` | Neutral note (e.g. unresolved reference when no library is attached) |

## Reference checking

`Validator(reference_checker=...)` turns unresolved UMS references into errors.
The resource manager provides a ready-made checker via `reference_checker()`.

Opaque, host-owned references (texture `Ref`s) use a separate
`asset_checker`. When it is set, an unresolved texture reference is an error;
otherwise the validator falls back to the `reference_checker` and finally to an
informational `TEXTURE_UNCHECKED` note. This lets UUID-style asset ids stay
opaque to UMS while still being checkable by the host that owns them.
