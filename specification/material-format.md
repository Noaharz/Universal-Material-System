# `.material` — Material Definition

A `.material` file is the central description of a material. It ties together
composition, structures, properties, models and optional variants.

## Sections

### Identity (required)

`Id`, `Name`, `Category`.

### Composition (optional)

Chemical composition, constituents and amounts, purity, concentration.

### Structures (optional)

References to structure definitions and their role:

```
Structures:
    - Ref: "structures/water.structure"
      Role: Molecule
```

A material may reference several structures and need not reference an atomic
structure at all.

### Properties (optional)

A property is either a fixed quantity or a reference to a computational model:

```
Properties:
    Density: 997 kg/m^3
    ThermalConductivity:
        Model: WaterThermalConductivity
    RefractiveIndex:
        Model: WaterOpticalProperties
```

The material file decides *which* model is used; the model implementation lives
in a separate module (`ums.models`) and declares its inputs, validity range and
uncertainty.

### Models (optional)

Named model configurations (thermal, mechanical, optical, fluid, chemical,
phase-transition).

### Phases (optional)

Named phases with temperature bounds:

```
Phases:
    Solid:
        Max: 273.15 K
    Liquid:
        Min: 273.15 K
        Max: 373.15 K
```

### CompositionProfiles (optional)

Named composition variants of one definition:

```
CompositionProfiles:
    Pure:
        H2O: 100%
    Seawater:
        H2O: 96.5%
        DissolvedSalts: 3.5%
```

### Variants (optional)

Named or parameterised modifications with default parameters:

```
Variants:
    Seawater:
        Parameters:
            Salinity: 35 PSU
```

A separate `.variant` file format is not required for the first version.

### References (optional)

Structures, atom definitions, datasets, models, external resources.

## Rule

A material definition does not promise a specific physical fidelity. A
simplified realtime model and a scientific model can describe the same material
at different accuracy, prerequisites and computational cost.
