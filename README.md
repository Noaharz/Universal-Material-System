# Universal Material System (UMS)

A modular, extensible and scalable architecture for describing real materials
across **game engines**, **CAD / engineering tools**, **3D modelling**,
**physical simulation** and **scientific computing**.

An `.atom` defines *what an atomic type is*, an `.structure` defines *how
constituents are arranged and bonded*, and an `.material` defines *how a
material is composed and which properties and models it has*. Definitions are
stored separately, reference each other through stable IDs and logical resource
paths, and are shared by any number of objects and simulations.

```
.atom  ->  .structure  ->  .material  ->  Material Instance  ->  Runtime / Simulation
```

---

## 1. The three formats

| Format | Purpose | Example |
| --- | --- | --- |
| `.atom` | Atom type / chemical element | `library/elements/gold.atom` |
| `.structure` | Universal structure (molecule, crystal, ionic, polymer, network, amorphous, porous, composite, custom) | `library/structures/water.structure` |
| `.material` | Material composition, structures, properties, models, phases, variants | `library/materials/water.material` |

A molecule is not its own file format — it is a `StructureType: Molecular`
inside `.structure`. There is likewise no separate `.variant` format.

Example — `library/elements/gold.atom`:

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
```

Example — `library/materials/water.material`:

```text
MATERIAL

Version: 1

Identity:
    Id: "material.water"
    Name: "Water"
    Category: "Fluid"

Composition:
    H2O: 100%

Structures:
    - Ref: "structures/water.structure"
      Role: Molecule

Properties:
    Density:
        Model: WaterDensity
    ThermalConductivity: 0.6 W/(m*K)
    RefractiveIndex: 1.333
```

---

## 2. Directory layout

```
universal-material-system/
├── ums/                        # Python package (the implementation)
│   ├── units.py                # 7-dimensional SI units & quantities
│   ├── parser.py               # shared indentation grammar
│   ├── serializer.py           # definition -> text
│   ├── model/                  # atom / structure / material / instance models
│   ├── validation.py           # per-format validation rules
│   ├── resources.py            # resource manager (cache, deps, cycles)
│   ├── materialsystem.py       # resolve materials, instances, variants
│   ├── models/                 # computational property models
│   ├── runtime.py              # scenes & material assignments
│   ├── science.py              # thermal/mechanical solvers, mixing, atomistic
│   └── cli.py                  # `ums-cli`
├── cpp/                        # standalone C++20 reader (no dependencies, WASM-ready)
│   ├── include/ums/            # value, errors, units, parser, serializer, validation,
│   │                           #   reader, registry, library, fileio
│   ├── src/                    # core (fs-free) + fileio/library (filesystem)
│   ├── tools/umsdump.cpp       # inspection CLI
│   ├── tools/umsconf.cpp       # conformance CLI (parse/canonical/validate/resolve/units)
│   └── tests/                  # core_test + reader_test (CTest suite)
├── library/                    # Phase 5 example library
│   ├── elements/               # 10 atoms
│   ├── structures/             # 8 structures
│   └── materials/              # 9 materials
├── examples/                   # elements, structures, materials, instances, scenes
├── specification/             # formal format specification (Phase 1)
└── tests/                      # pytest suite (incl. C++ reader integration)
```

---

## 3. Quick start

```bash
pip install -e .            # optional; the package also runs from the repo root

# List the library
python -m ums.cli library -L library

# Validate a definition (parses, checks units, resolves references)
python -m ums.cli validate library/materials/water.material -L library

# Show the dependency graph  material -> structure -> atoms
python -m ums.cli deps materials/water.material -L library

# Resolve a material at a given temperature / profile / variant
python -m ums.cli resolve materials/water.material -L library --temperature "300 K" --profile Seawater

# Run solvers
python -m ums.cli solve materials/steel.material -L library -m mechanical
python -m ums.cli solve materials/gold.material -L library -m thermal

# Resolve an instance, or a whole scene with sharing statistics
python -m ums.cli instance examples/instances/ocean_water.instance -L library
python -m ums.cli scene examples/scenes/pool_scene.json -L library --resolve

# Re-format a document through the canonical serializer
python -m ums.cli fmt library/elements/gold.atom
```

---

## 4. Python API

```python
from ums import ResourceManager, MaterialSystem, ThermalSolver
from ums.units import Quantity, resolve_unit

manager = ResourceManager(["library"])
system = MaterialSystem(manager)

water = system.resolve(
    "materials/water.material",
    state={"Temperature": Quantity(300, resolve_unit("K"))},
)
print(water.phase())                       # Liquid
print(water.resolve_property("Density"))   # 996.558 kg/m^3 (model-evaluated)

# Dependency graph and reference checking
print(manager.dependencies("materials/water.material"))
assert manager.missing_references() == {}
manager.check_cycles()

# Scientific solver
solver = ThermalSolver.from_material(water)
solution = solver.steady_state_1d(
    Quantity(1.0, resolve_unit("m")),
    Quantity(273.15, resolve_unit("K")),
    Quantity(373.15, resolve_unit("K")),
)
print(solution.heat_flux)
```

### Resource manager guarantees

`ums.resources.ResourceManager` discovers resources by logical path
(`elements/gold.atom`) or stable ID (`element.gold`), caches definitions so a
shared atom is never loaded twice, computes the dependency graph, detects
cycles (`CyclicDependencyError`), reports missing references and is thread-safe.
An `asyncio`-based `aload()` enables background loading.

### Scenes and runtime

`ums.runtime.Scene` stores assignments (`object -> shared material definition +
instance parameters`). Millions of objects reference the same definition and
`SceneRuntime.memory_report()` quantifies the sharing. Definitions are loaded
once; only per-object parameters are stored per assignment.

### Computational models

Properties may be fixed values or references to computational models
(`{Model: WaterDensity}`). Models declare their inputs, validity range and
uncertainty via `ModelMetadata`, so a realtime model and a scientific model can
describe the same material at different fidelity. Register your own via
`ums.models.register_model`.

---

## 5. C++ reader (`cpp/`)

A standalone, dependency-free **C++20** library that reads all four formats
(`.atom`, `.structure`, `.material`, `.instance`) with the same grammar as the
Python parser — intended for embedding in engines and tools that cannot run
Python, including **WebAssembly**. It mirrors the Python reference: the same
unit system (`Quantity`, compound units such as `W/(m*K)`), a serializer that
writes byte-for-byte the same canonical text, and the same validation rules.

Key pieces:

- `value.hpp` — generic `Value` tree (null/bool/int/float/string/list/map).
- `errors.hpp` — `UmsError`, `ParseError` (with **line and column**), `UnitError`, …
- `units.hpp` — 7-dimension SI vector, `Unit`, `Quantity`, `parse_unit`, `parse_quantity`.
- `parser.hpp` — buffer-based (`parse_buffer` / `parse_document(std::string_view)`), no I/O.
- `serializer.hpp` — `serialize_document` reproduces the Python output exactly.
- `validation.hpp` — `Validator` producing the same codes/severities/paths as Python.
- `registry.hpp` — fs-free `ResourceRegistry` (IDs, logical paths, dependency graph,
  cycles, missing references); resolves refs by path **or** stable ID.
- `reader.hpp` — typed `AtomDefinition`, `StructureDefinition`, `MaterialDefinition`,
  `MaterialInstance`.
- `library.hpp`, `fileio.hpp` — filesystem layer (search paths, indexing, `parse_file`).

The entire core is I/O-free and therefore WASM-ready: build with
`-DUMS_NO_FILESYSTEM=ON` to compile only the buffer/registry/validate/serialize
core (no `std::filesystem`, no threads).

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j4
ctest --test-dir cpp/build

cpp/build/umsdump library/elements/gold.atom                 # typed summary
cpp/build/umsdump --lib library --list                       # index a library
cpp/build/umsdump --lib examples material.copper             # lookup by ID
cpp/build/umsdump --lib examples --tree structures/titanium_crystal.structure

cpp/build/umsconf canonical library/elements/gold.atom       # deterministic re-serialization
cpp/build/umsconf validate library/materials/gold.material   # same rules as Python
cpp/build/umsconf resolve element.gold --lib library         # reference resolution
cpp/build/umsconf unit "W/(m*K)"                             # unit parsing
```

```cpp
#include "ums/library.hpp"
#include "ums/reader.hpp"

ums::ResourceLibrary library({"library"});
library.index();
const ums::Document* doc = library.load("materials/water.material");
if (doc) {
    ums::MaterialDefinition water = ums::read_material(*doc);
    auto density = water.property("Density");
    for (const auto& ref : water.structure_refs()) { /* ... */ }
}
```

Verification is twofold: `tests/test_cpp_reader.py` exercises the reader against
the real library, and `tests/test_cpp_conformance.py` runs every library/example
document (plus invalid fixtures) through **both** implementations, asserting
identical parse results, canonical serialization, validation issues
(code/severity/path/subject) and unit arithmetic.

---

## 6. Development status (Phase plan)

| Phase | Content | Status |
| --- | --- | --- |
| 1 | Format specification (`.atom`, `.structure`, `.material`, units, IDs, versioning, validation) | done (`specification/`) |
| 2 | Parser & validator | done (`ums/parser.py`, `ums/validation.py`) |
| 3 | Resource manager (references, dependencies, cache, cycles) | done (`ums/resources.py`) |
| 4 | Materialsystem (definitions, composition, instances, parameters, variants) | done (`ums/materialsystem.py`) |
| 5 | Example library (water, gold, carbon/diamond, NaCl, iron, polymer, …) | done (`library/`) |
| 6 | Runtime integration (scene assignments, shared definitions, memory optimization) | done (`ums/runtime.py`) |
| 7 | Scientific extensions (property models, thermal/mechanical solvers, mixing, atomistic state) | done (`ums/science.py`, `ums/models/`) |

## 7. Tests

```bash
python -m pytest          # Python suite + C++ reader/conformance integration (102 tests)
ctest --test-dir cpp/build
```
