import pytest

from ums.errors import ParseError
from ums.parser import DocumentType, parse_document


WATER = """STRUCTURE

Version: 1

Identity:
    Id: "structure.water"
    Name: "Water"
    StructureType: Molecular

Composition:
    - AtomRef: "elements/hydrogen.atom"
      Count: 2

    - AtomRef: "elements/oxygen.atom"
      Count: 1

Topology:
    Atoms:
        - Id: H1
          Type: "elements/hydrogen.atom"
        - Id: O1
          Type: "elements/oxygen.atom"
    Bonds:
        - From: H1
          To: O1
          Type: Covalent

Geometry:
    BondAngle: 104.5 deg

Periodicity:
    Dimensions: 3
    PeriodicAxes: [true, true, true]
"""


def test_document_type_and_sections():
    doc_type, sections = parse_document(WATER)
    assert doc_type is DocumentType.STRUCTURE
    assert sections["Version"] == 1
    assert sections["Identity"]["Id"] == "structure.water"
    assert sections["Identity"]["StructureType"] == "Molecular"


def test_sequence_of_mappings():
    _, sections = parse_document(WATER)
    composition = sections["Composition"]
    assert composition[0] == {"AtomRef": "elements/hydrogen.atom", "Count": 2}
    assert composition[1]["Count"] == 1


def test_nested_topology_and_flow_list():
    _, sections = parse_document(WATER)
    assert sections["Topology"]["Atoms"][0]["Id"] == "H1"
    assert sections["Topology"]["Bonds"][0]["Type"] == "Covalent"
    assert sections["Periodicity"]["PeriodicAxes"] == [True, True, True]


def test_scalars_are_typed():
    _, sections = parse_document(WATER)
    assert sections["Version"] == 1
    assert sections["Geometry"]["BondAngle"] == "104.5 deg"
    assert sections["Periodicity"]["Dimensions"] == 3


def test_comments_and_blank_lines_ignored():
    text = "# comment\nATOM\n\nVersion: 1\n# another\nIdentity:\n    Id: \"element.x\"\n"
    doc_type, sections = parse_document(text)
    assert doc_type is DocumentType.ATOM
    assert sections["Identity"]["Id"] == "element.x"


def test_unknown_type_raises():
    with pytest.raises(ParseError):
        parse_document("GIBBERISH\nVersion: 1\n")


def test_empty_document_raises():
    with pytest.raises(ParseError):
        parse_document("\n\n# only comments\n")
