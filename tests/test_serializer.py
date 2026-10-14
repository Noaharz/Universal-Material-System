from pathlib import Path

import pytest

from ums.parser import parse_document
from ums.serializer import serialize_document

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def _all_documents():
    for path in sorted(LIBRARY.rglob("*")):
        if path.suffix in (".atom", ".structure", ".material", ".instance"):
            yield path


@pytest.mark.parametrize("path", list(_all_documents()), ids=lambda p: p.name)
def test_roundtrip_is_stable(path):
    original_text = path.read_text(encoding="utf-8")
    doc_type, sections = parse_document(original_text, str(path))
    rendered = serialize_document(doc_type, sections)
    doc_type2, sections2 = parse_document(rendered, str(path))
    assert doc_type2 is doc_type
    assert sections2 == sections


def test_roundtrip_quotes_references():
    text = (
        "MATERIAL\n\nVersion: 1\n\nIdentity:\n    Id: \"material.x\"\n    Name: \"X\"\n\n"
        "Structures:\n    - Ref: \"structures/water.structure\"\n      Role: Molecule\n"
    )
    doc_type, sections = parse_document(text)
    rendered = serialize_document(doc_type, sections)
    assert '"structures/water.structure"' in rendered
    assert '"material.x"' in rendered
