import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ums import ResourceManager, MaterialSystem  # noqa: E402

LIBRARY = ROOT / "library"


@pytest.fixture(scope="session")
def library_path():
    return LIBRARY


@pytest.fixture()
def manager(library_path):
    manager = ResourceManager([library_path])
    manager.index()
    return manager


@pytest.fixture()
def system(manager):
    return MaterialSystem(manager)
