from ums.model import AtomDefinition, MaterialDefinition, StructureDefinition
from ums.parser import parse_document
from ums.units import Quantity


ATOM_TEXT = """ATOM

Version: 1

Identity:
    Id: "element.gold"
    Name: "Gold"
    Symbol: "Au"
    AtomicNumber: 79

Properties:
    AtomicMass: 196.96657 u
    AtomicRadius: 144 pm
"""

MATERIAL_TEXT = """MATERIAL

Version: 2

Identity:
    Id: "material.water"
    Name: "Water"
    Category: "Fluid"

Structures:
    - Ref: "structures/water.structure"
      Role: Molecule

Properties:
    Density:
        Model: WaterDensity
    HeatCapacity: 4182 J/(kg*K)

Variants:
    Seawater:
        Parameters:
            Salinity: 35 PSU

CompositionProfiles:
    Seawater:
        H2O: 96.5%
        DissolvedSalts: 3.5%
"""


def test_atom_from_sections():
    _, sections = parse_document(ATOM_TEXT)
    atom = AtomDefinition.from_sections(sections)
    assert atom.id == "element.gold"
    assert atom.symbol == "Au"
    assert atom.atomic_number == 79
    assert isinstance(atom.atomic_mass, Quantity)
    assert atom.atomic_mass.value == 196.96657


def test_material_from_sections():
    _, sections = parse_document(MATERIAL_TEXT)
    material = MaterialDefinition.from_sections(sections)
    assert material.id == "material.water"
    assert material.version == 2
    assert material.category == "Fluid"
    assert material.structure_refs() == ["structures/water.structure"]
    assert isinstance(material.properties["HeatCapacity"], Quantity)
    assert material.properties["Density"] == {"Model": "WaterDensity"}
    assert "Seawater" in material.variants
    assert material.variants["Seawater"].parameters["Salinity"].value == 35
    assert "Seawater" in material.composition_profiles


def test_structure_atom_refs_deduplicated(library_path):
    from ums.resources import ResourceManager

    manager = ResourceManager([library_path])
    structure = manager.load_structure("structures/water.structure")
    refs = structure.atom_refs()
    assert "elements/hydrogen.atom" in refs
    assert "elements/oxygen.atom" in refs
    assert len(refs) == len(set(refs))
    assert len(structure.atoms) == 3
    assert len(structure.bonds) == 2
