from ums.model import AtomDefinition, MaterialDefinition, StructureDefinition
from ums.parser import parse_document
from ums.validation import Severity, Validator


def _resource(text):
    doc_type, sections = parse_document(text)
    if doc_type.value == "ATOM":
        return AtomDefinition.from_sections(sections)
    if doc_type.value == "STRUCTURE":
        return StructureDefinition.from_sections(sections)
    return MaterialDefinition.from_sections(sections)


def test_valid_atom_passes():
    atom = _resource(
        """ATOM

Version: 1

Identity:
    Id: "element.gold"
    Name: "Gold"
    Symbol: "Au"
    AtomicNumber: 79

Properties:
    AtomicMass: 196.96657 u
"""
    )
    report = Validator().validate(atom)
    assert report.is_valid


def test_bad_dimension_detected():
    atom = _resource(
        """ATOM

Version: 1

Identity:
    Id: "element.gold"
    Name: "Gold"

Properties:
    AtomicMass: 196.96657 K
"""
    )
    report = Validator().validate(atom)
    assert not report.is_valid
    assert any(i.code == "DIMENSION_MISMATCH" for i in report.issues)


def test_missing_id_is_error():
    atom = _resource("ATOM\n\nVersion: 1\n\nIdentity:\n    Name: X\n")
    report = Validator().validate(atom)
    assert any(i.code == "ID_MISSING" for i in report.issues)


def test_duplicate_topology_ids():
    structure = _resource(
        """STRUCTURE

Version: 1

Identity:
    Id: "structure.x"
    Name: "X"
    StructureType: Molecular

Topology:
    Atoms:
        - Id: A1
          Type: "elements/hydrogen.atom"
        - Id: A1
          Type: "elements/oxygen.atom"
"""
    )
    report = Validator().validate(structure)
    assert any(i.code == "ATOM_LOCAL_ID_DUP" for i in report.issues)


def test_bond_to_unknown_atom():
    structure = _resource(
        """STRUCTURE

Version: 1

Identity:
    Id: "structure.x"
    Name: "X"
    StructureType: Molecular

Topology:
    Atoms:
        - Id: A1
          Type: "elements/hydrogen.atom"
    Bonds:
        - From: A1
          To: Z9
          Type: Covalent
"""
    )
    report = Validator().validate(structure)
    assert any(i.code == "BOND_ENDPOINT_UNKNOWN" for i in report.issues)


def test_unresolved_reference_with_checker():
    material = _resource(
        """MATERIAL

Version: 1

Identity:
    Id: "material.x"
    Name: "X"

Structures:
    - Ref: "structures/missing.structure"
"""
    )
    report = Validator(reference_checker=lambda ref: False).validate(material)
    assert any(i.code == "REF_UNRESOLVED" for i in report.issues)


def test_property_model_without_name():
    material = _resource(
        """MATERIAL

Version: 1

Identity:
    Id: "material.x"
    Name: "X"

Properties:
    Density:
        Foo: 1
"""
    )
    report = Validator().validate(material)
    assert any(i.code == "PROPERTY_MODEL_MISSING" for i in report.issues)
