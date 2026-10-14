# Universal Material System — Architecture Specification

Version 2.0.0 (draft)

This specification defines the **Universal Material System (UMS)**, a modular
architecture for describing real materials across game engines, CAD tools, 3D
modelling, physical simulation and scientific computing.

## 1. Design principle

Atom definitions, structure models and material definitions are stored
**separately**. They can be developed, reused, loaded and versioned
independently and reference each other only through stable IDs and logical
resource paths.

Three primary file formats exist:

| Format | Question it answers | Example |
| --- | --- | --- |
| `.atom` | What is a given atomic type? | `elements/gold.atom` |
| `.structure` | How are constituents arranged and bonded? | `structures/water.structure` |
| `.material` | How is a material composed and which properties/models does it have? | `materials/water.material` |

Molecules, crystals, polymers and networks are **structure types** within the
single `.structure` format — there is no separate `.molecule` format.

## 2. Layers

```
.atom  ->  .structure  ->  .material  ->  Material Instance  ->  Runtime / Simulation
```

This is a conceptual overview, not a strict linear dependency. A material may
reference several structures; a material need not reference an atomic structure
at all (e.g. a purely optical material).

## 3. Specifications

| Document | Contents |
| --- | --- |
| [format-grammar.md](format-grammar.md) | Token/indentation grammar shared by all formats |
| [units.md](units.md) | 7-dimensional SI engine and quantity syntax |
| [atom-format.md](atom-format.md) | `.atom` sections and fields |
| [structure-format.md](structure-format.md) | `.structure` sections and structure types |
| [material-format.md](material-format.md) | `.material` sections, variants, properties |
| [instance-and-runtime.md](instance-and-runtime.md) | Instances, mixes, scenes, runtime split |
| [references-and-ids.md](references-and-ids.md) | Logical paths, stable IDs, resource manager |
| [versioning.md](versioning.md) | Versioning rules |
| [validation.md](validation.md) | Validation rules per format |

## 4. Separation of static and dynamic data

Static definitions (`.atom`, `.structure`, `.material`) describe reusable types.
Instance data (material assignment, local parameters, mix composition) and
dynamic simulation data (positions, temperature/pressure fields, stresses) are
stored separately at runtime. A definition must never be duplicated per object
or per simulation step.
