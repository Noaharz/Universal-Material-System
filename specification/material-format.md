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

A variant may also override the `Appearance` and `Contact` blocks field by
field, so a single material definition covers several look-and-feel presets:

```
Variants:
    Rough:
        Appearance:
            Roughness: 0.9
```

A separate `.variant` file format is not required for the first version.

### Appearance (optional)

A render-facing PBR metallic-roughness block using glTF 2.0 semantics. Only
fields that are present are stored; absent fields fall back to documented
defaults. Turning the data into shaders or GPU state is the host's job.

```
Appearance:
    BaseColor: [0.8, 0.6, 0.5, 1.0]
    Metallic: 0.0
    Roughness: 0.4
    EmissionColor: [0, 0, 0]
    EmissionStrength: 0.0
    Opacity: 1.0
    AlphaMode: Opaque        # Opaque | Mask | Blend
    AlphaCutoff: 0.5
    DoubleSided: false
    NormalScale: 1.0
    OcclusionStrength: 1.0
    Textures:
        BaseColor:
            Ref: "textures/wood_albedo.png"
            UVScale: [1, 1]
            UVOffset: [0, 0]
            UVSet: 0
        Normal:
            Ref: "textures/wood_normal.png"
```

* `BaseColor` takes 3 or 4 components in `[0, 1]`. With 4 components, `[3]` is
  the alpha and takes precedence over `Opacity`.
* Texture slots are `BaseColor`, `MetallicRoughness`, `Normal`, `Occlusion` and
  `Emission`. Each carries a `Ref` plus optional `UVScale`, `UVOffset` and
  `UVSet`. The `Ref` is opaque - it may be a logical UMS path or a host asset id
  such as a UUID. Resolving it is the host's job (see `references-and-ids.md`);
  UMS only validates the shape.
* Unknown `Appearance` fields and unknown texture slots are preserved so hosts
  can extend the block without breaking round-trips.

### Contact (optional)

Contact physics parameters and the combine rules used to blend two materials'
values:

```
Contact:
    StaticFriction: 0.6
    DynamicFriction: 0.5
    Restitution: 0.1
    FrictionCombine: GeometricMean   # Average | Minimum | Multiply | Maximum | GeometricMean
    RestitutionCombine: Maximum
```

### ContactPairs (optional)

Per-other-material overrides of the contact parameters:

```
ContactPairs:
    - Other: "material.ice"
      StaticFriction: 0.05
      Restitution: 0.0
```

`Other` may be a logical path or a stable ID. Engine-physics quantities are
unchanged: `Density`, `YoungsModulus` and `PoissonRatio` remain in `Properties`.

### References (optional)

Structures, atom definitions, datasets, models, external resources.

## Rule

A material definition does not promise a specific physical fidelity. A
simplified realtime model and a scientific model can describe the same material
at different accuracy, prerequisites and computational cost.
