import asyncio

from ums.runtime import Scene, SceneRuntime
from ums.units import Quantity, resolve_unit


def _scene(manager):
    scene = Scene("test")
    for i in range(1000):
        scene.assign(f"obj/{i}", "materials/water.material", state={"Temperature": Quantity(293, resolve_unit("K"))})
    scene.assign("obj/gold", "materials/gold.material")
    return scene


def test_scene_sharing_statistics(system):
    scene = _scene(system.manager)
    stats = scene.sharing_statistics()
    assert stats["assignments"] == 1001
    assert stats["unique_materials"] == 2
    assert stats["most_shared"] == 1000
    assert stats["savings"] > 0


def test_scene_runtime_resolves(system):
    scene = _scene(system.manager)
    runtime = SceneRuntime(scene, system)
    resolved = runtime.resolve_all()
    assert resolved["obj/0"].name == "Water"
    assert resolved["obj/gold"].name == "Gold"


def test_scene_from_dict(system):
    data = {
        "name": "mini",
        "assignments": [
            {"object": "a", "material": "materials/water.material", "state": {"Temperature": "300 K"}},
            {"object": "b", "material": "materials/gold.material"},
        ],
    }
    scene = Scene.from_dict(data)
    runtime = SceneRuntime(scene, system)
    report = runtime.memory_report()
    assert report["assignments"] == 2
    assert runtime.resolve(scene.assignments[0]).phase() == "Liquid"


def test_preload_async(system):
    scene = _scene(system.manager)
    runtime = SceneRuntime(scene, system)
    asyncio.run(runtime.preload())
    assert runtime.manager.has("materials/water.material")
