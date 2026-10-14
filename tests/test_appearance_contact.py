"""Appearance, Contact and unknown-section preservation."""

from ums.materialsystem import MaterialSystem
from ums.model import MaterialDefinition, MaterialInstance
from ums.parser import parse_document
from ums.resources import ResourceManager
from ums.serializer import serialize_document
from ums.validation import Severity, Validator

MATERIAL_TEXT = """MATERIAL

Version: 1

Identity:
    Id: "material.skin"
    Name: "Skin"

Appearance:
    BaseColor: [0.8, 0.6, 0.5, 1.0]
    Metallic: 0.0
    Roughness: 0.4
    AlphaMode: Opaque

Contact:
    StaticFriction: 0.8
    DynamicFriction: 0.6
    Restitution: 0.0
    FrictionCombine: Average

ContactPairs:
    - Other: "material.cloth"
      StaticFriction: 0.5

CustomExtension:
    Foo: "bar"

Properties:
    Density: 1100 kg/m^3
"""


def _material(text=MATERIAL_TEXT):
    _, sections = parse_document(text)
    return MaterialDefinition.from_sections(sections)


def test_appearance_values_and_defaults():
    material = _material()
    appearance = material.appearance
    assert appearance.present
    assert appearance.get("BaseColor") == [0.8, 0.6, 0.5, 1.0]
    assert appearance.get("Roughness") == 0.4
    assert appearance.effective_opacity() == 1.0
    # documented default for an absent field
    assert appearance.get("NormalScale") == 1.0
    assert not appearance.has("NormalScale")


def test_contact_and_contact_pairs():
    material = _material()
    assert material.contact.get("Restitution") == 0.0
    assert material.contact.get("FrictionCombine") == "Average"
    assert len(material.contact_pairs) == 1
    assert material.contact_pairs[0].other == "material.cloth"
    assert material.contact_pairs[0].get("StaticFriction") == 0.5


def test_unknown_section_preserved_on_roundtrip():
    material = _material()
    assert material.extra == {"CustomExtension": {"Foo": "bar"}}
    text = serialize_document(parse_document(MATERIAL_TEXT)[0], material.to_sections())
    reparsed = _material(text)
    assert reparsed.extra == material.extra
    assert reparsed.appearance.values == material.appearance.values
    assert "CustomExtension" in text


def test_unknown_sections_preserved_atom_and_structure():
    atom_text = 'ATOM\n\nVersion: 1\n\nIdentity:\n    Id: "element.x"\n    Name: "X"\n\nCustom:\n    A: 1\n'
    _, sections = parse_document(atom_text)
    from ums.model import AtomDefinition

    atom = AtomDefinition.from_sections(sections)
    assert atom.extra == {"Custom": {"A": 1}}
    assert atom.to_sections()["Custom"] == {"A": 1}


def test_variant_and_instance_override_merge():
    text = MATERIAL_TEXT.replace(
        "CustomExtension:",
        "Variants:\n    Rough:\n        Appearance:\n            Roughness: 0.9\n\nCustomExtension:",
    )
    material = _material(text)
    assert material.variants["Rough"].appearance == {"Roughness": 0.9}

    manager = ResourceManager()
    manager.register(material, "material.skin")
    system = MaterialSystem(manager)
    resolved = system.resolve(material, variant="Rough")
    assert resolved.appearance().get("Roughness") == 0.9
    assert resolved.appearance().get("Metallic") == 0.0

    instance = MaterialInstance(
        instance_id="i1",
        definition_ref="material.skin",
        appearance={"Metallic": 0.5},
    )
    resolved_instance = system.resolve(instance)
    assert resolved_instance.appearance().get("Metallic") == 0.5
    assert resolved_instance.appearance().get("Roughness") == 0.4


def test_appearance_validation():
    text = """MATERIAL

Version: 1

Identity:
    Id: "material.bad"
    Name: "Bad"

Appearance:
    BaseColor: [1, 2]
    Metallic: 5
    AlphaMode: Glow
    Textures:
        Normal:
            UVScale: [1]

Contact:
    FrictionCombine: Sometimes
    Restitution: 2
"""
    report = Validator().validate(_material(text))
    codes = [(i.severity.value, i.code, i.path) for i in report.issues]
    assert ("error", "APPEARANCE_LIST", "Appearance.BaseColor") in codes
    assert ("error", "APPEARANCE_RANGE", "Appearance.Metallic") in codes
    assert ("error", "APPEARANCE_ENUM", "Appearance.AlphaMode") in codes
    assert ("error", "TEXTURE_UV", "Appearance.Textures.Normal.UVScale") in codes
    assert ("error", "CONTACT_ENUM", "Contact.FrictionCombine") in codes
    assert ("error", "CONTACT_RANGE", "Contact.Restitution") in codes


def test_texture_reference_resolution():
    text = MATERIAL_TEXT.replace(
        "    AlphaMode: Opaque\n",
        '    AlphaMode: Opaque\n    Textures:\n        BaseColor:\n            Ref: "textures/skin.png"\n',
    )
    material = _material(text)

    unchecked = Validator().validate(material)
    assert any(i.code == "TEXTURE_UNCHECKED" for i in unchecked.issues)

    resolved = Validator(asset_checker=lambda ref: ref == "textures/skin.png").validate(material)
    assert not any(i.code in ("TEXTURE_UNRESOLVED", "TEXTURE_UNCHECKED") for i in resolved.issues)

    missing = Validator(asset_checker=lambda ref: False).validate(material)
    issue = next(i for i in missing.issues if i.code == "TEXTURE_UNRESOLVED")
    assert issue.severity is Severity.ERROR
