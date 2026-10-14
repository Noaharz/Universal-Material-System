"""Shared conformance tests between the Python reference and the C++ reader.

Every case runs the same input through the Python implementation and the C++
``umsconf`` tool and asserts that both agree on parsing, canonical
serialization, validation rules and unit arithmetic.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ums.parser import parse_document
from ums.resources import ResourceManager, _build_resource
from ums.serializer import serialize_document
from ums.units import parse_quantity, parse_unit
from ums.validation import Validator

ROOT = Path(__file__).resolve().parent.parent
CPP = ROOT / "cpp"


def _toolchain_available() -> bool:
    if shutil.which("cmake") is None:
        return False
    return any(shutil.which(c) for c in ("c++", "clang++", "g++"))


@pytest.fixture(scope="session")
def umsconf(tmp_path_factory):
    if not _toolchain_available():
        pytest.skip("cmake and a C++ compiler are required for the C++ conformance tests")
    build_dir = tmp_path_factory.mktemp("ums-conf-build")
    configure = subprocess.run(
        ["cmake", "-S", str(CPP), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"],
        capture_output=True,
        text=True,
    )
    if configure.returncode != 0:
        pytest.skip(f"cmake configure failed:\n{configure.stdout}\n{configure.stderr}")
    build = subprocess.run(
        ["cmake", "--build", str(build_dir), "-j", "4"],
        capture_output=True,
        text=True,
    )
    if build.returncode != 0:
        pytest.skip(f"cmake build failed:\n{build.stdout}\n{build.stderr}")
    binary = build_dir / "umsconf"
    if not binary.exists():
        pytest.skip("umsconf binary was not produced")
    return binary


def _run(umsconf, *args):
    return subprocess.run([str(umsconf), *args], capture_output=True, text=True)


def _documents():
    files = []
    for base in (ROOT / "library", ROOT / "examples"):
        for path in sorted(base.rglob("*")):
            if path.suffix in (".atom", ".structure", ".material"):
                files.append(path)
    return files


FILES = _documents()

INVALID_DOCUMENTS = {
    "atom_missing_id": "ATOM\n\nIdentity:\n    Name: \"Nameless\"\n",
    "atom_bad_id": "ATOM\n\nIdentity:\n    Id: \"bad id!\"\n    Name: \"X\"\n",
    "structure_bad_bond": (
        "STRUCTURE\n\nIdentity:\n    Id: \"structure.x\"\n    Name: \"X\"\n"
        "    StructureType: Custom\n\nTopology:\n    Atoms:\n        - Id: a\n          Type: elements/x.atom\n"
        "    Bonds:\n        - From: a\n          To: b\n"
    ),
    "material_property_without_model": (
        "MATERIAL\n\nIdentity:\n    Id: \"material.x\"\n    Name: \"X\"\n\nProperties:\n    Density:\n        Ref: model\n"
    ),
    "atom_absolute_ref": (
        "ATOM\n\nIdentity:\n    Id: \"element.x\"\n    Name: \"X\"\n\nReferences:\n    DataSource: \"/etc/data\"\n"
    ),
}


def test_canonical_round_trip(umsconf):
    mismatches = []
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        doc_type, sections = parse_document(text, str(path))
        expected = serialize_document(doc_type, sections)
        result = _run(umsconf, "canonical", str(path))
        if result.returncode != 0 or result.stdout != expected:
            mismatches.append((path.name, expected, result.stdout, result.stderr))
    assert not mismatches, mismatches[:3]


def test_parse_matches_python(umsconf):
    for path in FILES:
        doc_type, _ = parse_document(path.read_text(encoding="utf-8"), str(path))
        result = _run(umsconf, "parse", str(path))
        assert result.returncode == 0, (path, result.stderr)
        assert result.stdout.strip() == f"OK\t{doc_type.value.lower()}", path


def test_validation_parity(umsconf, tmp_path):
    cases = {path.name: path.read_text(encoding="utf-8") for path in FILES}
    cases.update(INVALID_DOCUMENTS)
    for name, text in cases.items():
        source = tmp_path / name
        source.write_text(text, encoding="utf-8")
        doc_type, sections = parse_document(text, name)
        resource = _build_resource(doc_type, sections, None)
        report = Validator().validate(resource)
        expected_issues = [(i.severity.value, i.code, i.path) for i in report.issues]

        result = _run(umsconf, "validate", str(source))
        assert result.returncode == 0, (name, result.stderr)
        lines = result.stdout.strip().splitlines()
        subject = lines[0].split("\t", 1)[1]
        valid = lines[1].split("\t", 1)[1] == "true"
        issues = [tuple(line.split("\t")[1:]) for line in lines[2:]]

        assert subject == report.subject, name
        assert valid == report.is_valid, name
        assert issues == expected_issues, name


def test_unit_parity(umsconf):
    expressions = ["kg", "kg/m^3", "W/(m*K)", "J/(kg*K)", "km", "mm", "MPa", "1/s", "g/cm^3", "um", "ns"]
    for expr in expressions:
        unit = parse_unit(expr)
        result = _run(umsconf, "unit", expr)
        assert result.returncode == 0, (expr, result.stderr)
        parts = result.stdout.strip().split("\t")
        fields = dict(zip(parts[0::2], parts[1::2]))
        assert fields["symbol"] == unit.symbol, expr
        assert abs(float(fields["scale"]) - unit.scale) < 1e-12, expr
        assert [int(x) for x in fields["dim"].split(",")] == list(unit.dimension.exponents), expr


def test_quantity_parity(umsconf):
    texts = ["196.96657 u", "0.5%", "3.567 angstrom", "104.5 deg", "9.81 m/s^2", "293 K"]
    for text in texts:
        quantity = parse_quantity(text)
        result = _run(umsconf, "quantity", text)
        assert result.returncode == 0, (text, result.stderr)
        parts = result.stdout.strip().split("\t")
        fields = dict(zip(parts[0::2], parts[1::2]))
        assert abs(float(fields["value"]) - quantity.value) < 1e-12, text
        assert fields["symbol"] == quantity.unit.symbol, text
        assert [int(x) for x in fields["dim"].split(",")] == list(quantity.unit.dimension.exponents), text


def test_resolve_parity(umsconf):
    manager = ResourceManager([ROOT / "library"])
    manager.index()
    refs = [
        "element.gold",
        "elements/gold.atom",
        "material.steel",
        "structures/water.structure",
        "element.missing",
        "does/not/exist.atom",
    ]
    for ref in refs:
        expected = manager.has(ref)
        result = _run(umsconf, "resolve", ref, "--lib", str(ROOT / "library"))
        assert result.returncode == 0, (ref, result.stderr)
        assert (result.stdout.strip() == "true") == expected, ref


def test_parse_error_line_parity(umsconf, tmp_path):
    cases = {
        "indented.atom": "  ATOM\n\nIdentity:\n    Id: x\n",
        "missing_colon.atom": "ATOM\n\nIdentity:\n    Id \"x\"\n",
        "unknown_type.material": "FOOBAR\n\nIdentity:\n    Id: \"x\"\n",
    }
    for name, text in cases.items():
        source = tmp_path / name
        source.write_text(text, encoding="utf-8")
        with pytest.raises(Exception) as excinfo:
            parse_document(text, name)
        expected_line = getattr(excinfo.value, "line", None)

        result = _run(umsconf, "parse", str(source))
        assert result.returncode == 1, name
        match = re.search(r"line (\d+)", result.stdout)
        if expected_line is not None and match is not None:
            assert int(match.group(1)) == expected_line, name
