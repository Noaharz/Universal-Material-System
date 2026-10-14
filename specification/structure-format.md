# `.structure` — Universal Structure Definition

A `.structure` file describes the composition, arrangement and bonding of
constituents. It is deliberately **not** limited to molecules.

## Structure types

`StructureType` selects which sections are meaningful:

`Molecular`, `Crystal`, `Ionic`, `Polymer`, `Network`, `Amorphous`, `Porous`,
`Composite`, `Custom`.

The actual fields depend on the type: a molecule needs bonds and molecular
geometry, a crystal needs unit-cell and periodicity data. All types are loaded,
validated, referenced and versioned through the same functions.

## Sections

### Identity (required)

`Id`, `Name`, `StructureType`.

### Composition (optional)

A list of constituent entries:

```
Composition:
    - AtomRef: "elements/hydrogen.atom"
      Count: 2
    - AtomRef: "elements/oxygen.atom"
      Count: 1
```

`AtomRef` is a logical resource path. `Count` or `Ratio` gives the amount.
Substructures may be listed as well.

### Topology (optional)

```
Topology:
    Atoms:
        - Id: H1
          Type: "elements/hydrogen.atom"
    Bonds:
        - From: H1
          To: O1
          Type: Covalent
```

Local atom `Id`s must be unique; bonds must reference declared local atoms.

### Geometry (optional)

Coordinates, bond lengths, angles, local coordinate systems.

### Crystal (optional, for crystals)

`LatticeType`, `BravaisLattice`, `SpaceGroup`, `LatticeParameter`.

### Periodicity (optional)

`Dimensions` and `PeriodicAxes: [true, true, true]`.

### Models, Substructures, References (optional)

Structure-related models; nested substructures; `AtomDefinitions`,
`Substructures` and external datasets.

## Examples

Water (Molecular) and diamond (Crystal) examples are provided in
`library/structures/`. Rule: `.structure` describes the structure, not the whole
behaviour of a real material — structure data and material properties are
handled separately.
