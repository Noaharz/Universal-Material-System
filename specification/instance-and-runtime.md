# Instances, Mixes and Runtime

## 1. Material definition vs. material instance

A **material definition** (`materials/water.material`) is a reusable type. A
**material instance** is a concrete use of that definition in a scene, CAD model
or simulation.

Instances store a reference to the shared definition plus instance-local state
and parameters:

```
INSTANCE

Version: 1

Identity:
    Id: "instance.oceanwater"
    Name: "OceanWater"

Definition: "materials/water.material"
Variant: "Seawater"

State:
    Temperature: 285 K
    Pressure: parameterized

Parameters:
    Salinity: 35 PSU
```

Instances need not have their own file; they may exist as runtime objects.

## 2. Mixes

A material instance may be composed from several material definitions:

```
BaseMaterial: "materials/water.material"

Components:
    - MaterialRef: "materials/sodium_chloride.material"
      Concentration: 0.5%
```

The concentration basis (mass / amount / volume fraction) must be stated by the
consuming model. Not every mixture is a linear combination — choose an
appropriate mixing model (`linear`, `harmonic`, `geometric`, …).

## 3. States and phases

Distinguish carefully:

* **Phase** — solid, liquid, gas (function of pressure, temperature, composition)
* **Thermodynamic state** — temperature, pressure, ...
* **Material state** — stress, strain, viscosity state, ...
* **Spatial fields** — locally varying temperature/pressure/concentration

State data is never stored as a new material definition. Spatially resolved
simulations keep fields and state in dedicated runtime/simulation structures.

## 4. Scenes

A scene stores **assignments**: an object ID, a reference to a shared material
definition, an optional instance, and optional local parameters/state. Millions
of objects can reference one definition without duplicating it. See
`ums.runtime.Scene` and `ums.runtime.SceneRuntime`.
