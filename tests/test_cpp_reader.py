import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CPP = ROOT / "cpp"


def _toolchain_available() -> bool:
    if shutil.which("cmake") is None:
        return False
    return any(shutil.which(c) for c in ("c++", "clang++", "g++"))


@pytest.fixture(scope="session")
def umsdump(tmp_path_factory):
    if not _toolchain_available():
        pytest.skip("cmake and a C++ compiler are required for the C++ reader tests")
    build_dir = tmp_path_factory.mktemp("ums-cpp-build")
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
    binary = build_dir / "umsdump"
    if not binary.exists():
        pytest.skip("umsdump binary was not produced")
    return binary


def _run(binary, *args):
    return subprocess.run([str(binary), *args], capture_output=True, text=True)


def test_atom_reader(umsdump):
    result = _run(umsdump, str(ROOT / "library" / "elements" / "gold.atom"))
    assert result.returncode == 0, result.stderr
    assert "type: atom" in result.stdout
    assert "id: element.gold" in result.stdout
    assert "symbol: Au" in result.stdout
    assert "atomic_number: 79" in result.stdout
    assert "AtomicMass = 196.967 u" in result.stdout


def test_structure_reader(umsdump):
    result = _run(umsdump, str(ROOT / "library" / "structures" / "water.structure"))
    assert result.returncode == 0, result.stderr
    assert "type: structure" in result.stdout
    assert "structure_type: Molecular" in result.stdout
    assert "atom_ref: elements/hydrogen.atom" in result.stdout
    assert "atom_ref: elements/oxygen.atom" in result.stdout


def test_material_reader(umsdump):
    result = _run(umsdump, str(ROOT / "library" / "materials" / "water.material"))
    assert result.returncode == 0, result.stderr
    assert "type: material" in result.stdout
    assert "id: material.water" in result.stdout
    assert "HeatCapacity = 4182 J/kg*K" in result.stdout


def test_instance_reader(umsdump):
    instance = ROOT / "examples" / "instances" / "ocean_water.instance"
    result = _run(umsdump, str(instance))
    assert result.returncode == 0, result.stderr
    assert "type: instance" in result.stdout
    assert "id: instance.oceanwater" in result.stdout
    assert "definition: materials/water.material" in result.stdout


def test_library_index_and_lookup(umsdump):
    result = _run(umsdump, "--lib", str(ROOT / "library"), "--list")
    assert result.returncode == 0, result.stderr
    assert "resources: 27" in result.stdout
    assert "[element.gold]" in result.stdout

    by_id = _run(umsdump, "--lib", str(ROOT / "library"), "material.steel")
    assert by_id.returncode == 0, by_id.stderr
    assert "id: material.steel" in by_id.stdout


def test_examples_library_isolated(umsdump):
    result = _run(umsdump, "--lib", str(ROOT / "examples"), "material.copper")
    assert result.returncode == 0, result.stderr
    assert "id: material.copper" in result.stdout
    assert "Density = 8960 kg/m^3" in result.stdout
