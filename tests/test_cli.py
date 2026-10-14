from pathlib import Path

from ums.cli import main

LIBRARY = Path(__file__).resolve().parent.parent / "library"


def test_library_command(capsys):
    rc = main(["library", "-L", str(LIBRARY)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "atom" in out
    assert "material" in out


def test_validate_command(capsys):
    rc = main(["validate", str(LIBRARY / "materials" / "water.material"), "-L", str(LIBRARY)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "VALID" in out


def test_resolve_command(capsys):
    rc = main(
        [
            "resolve",
            "materials/water.material",
            "-L",
            str(LIBRARY),
            "--temperature",
            "300 K",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "Water" in out
    assert "Liquid" in out
    assert "Density" in out


def test_solve_command(capsys):
    rc = main(["solve", "materials/gold.material", "-L", str(LIBRARY), "-m", "thermal"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "W/m^2" in out


def test_deps_command(capsys):
    rc = main(["deps", "materials/water.material", "-L", str(LIBRARY)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "water.structure" in out


def test_scene_command(capsys):
    scene = Path(__file__).resolve().parent.parent / "examples" / "scenes" / "pool_scene.json"
    rc = main(["scene", str(scene), "-L", str(LIBRARY), "--resolve"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "assignments" in out
    assert "Gold" in out


def test_instance_command(capsys):
    instance = Path(__file__).resolve().parent.parent / "examples" / "instances" / "ocean_water.instance"
    rc = main(["instance", str(instance), "-L", str(LIBRARY)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "OceanWater" in out


def test_validate_missing_file_reports_error(capsys):
    rc = main(["validate", str(LIBRARY / "does_not_exist.atom")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "PARSE ERROR" in err
