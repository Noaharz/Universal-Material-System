#include <cmath>
#include <iostream>
#include <string>

#include "ums/errors.hpp"
#include "ums/library.hpp"
#include "ums/reader.hpp"
#include "ums/writer.hpp"

namespace {

int failures = 0;

void check(bool condition, const std::string& label) {
    if (condition) {
        std::cout << "ok   - " << label << "\n";
    } else {
        std::cout << "FAIL - " << label << "\n";
        failures++;
    }
}

const char* kAtom = R"(ATOM

Version: 1

Identity:
    Id: "element.gold"
    Name: "Gold"
    Symbol: "Au"
    AtomicNumber: 79

Properties:
    AtomicMass: 196.96657 u
    Electronegativity: 2.54
)";

const char* kStructure = R"(STRUCTURE

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
)";

const char* kMaterial = R"(MATERIAL

Version: 1

Identity:
    Id: "material.gold"
    Name: "Gold"
    Category: "Metal"

Structures:
    - Ref: "structures/gold_crystal.structure"
      Role: Crystal

Properties:
    Density: 19300 kg/m^3
    MeltingPoint: 1337.33 K
)";

const char* kInstance = R"(INSTANCE

Version: 1

Identity:
    Id: "instance.poolwater_mix"
    Name: "PoolWaterMix"

BaseMaterial: "materials/water.material"

Components:
    - MaterialRef: "materials/sodium_chloride.material"
      Concentration: 0.5%

State:
    Temperature: 293 K
)";

const char* kAppearance = R"(MATERIAL

Version: 1

Identity:
    Id: "material.skin"
    Name: "Skin"

Appearance:
    BaseColor: [0.8, 0.6, 0.5, 1.0]
    Roughness: 0.4
    AlphaMode: Opaque
    Textures:
        Normal:
            Ref: "textures/skin_normal.png"

Contact:
    StaticFriction: 0.8
    Restitution: 0.0

ContactPairs:
    - Other: "material.cloth"
      StaticFriction: 0.6

ExtraSection:
    Foo: "bar"
)";

}  // namespace

int main(int argc, char** argv) {
    using namespace ums;

    Document atom_document = parse_document(kAtom);
    check(atom_document.type == DocumentType::Atom, "atom document type");
    AtomDefinition atom = read_atom(atom_document);
    check(atom.identity.id == "element.gold", "atom id");
    check(atom.identity.name == "Gold", "atom name");
    check(atom.symbol == "Au", "atom symbol");
    check(atom.atomic_number == 79, "atom atomic number");
    std::optional<Quantity> mass = atom.property("AtomicMass");
    check(mass.has_value(), "atom atomic mass is quantity");
    check(mass.has_value() && std::fabs(mass->value - 196.96657) < 1e-6, "atom atomic mass value");
    check(mass.has_value() && mass->unit.symbol == "u", "atom atomic mass unit");
    std::optional<Quantity> electronegativity = atom.property("Electronegativity");
    check(electronegativity.has_value() && electronegativity->unit.is_dimensionless(), "dimensionless property");

    Document structure_document = parse_document(kStructure);
    StructureDefinition structure = read_structure(structure_document);
    check(structure.identity.id == "structure.water", "structure id");
    check(structure.structure_type == "Molecular", "structure type");
    std::vector<std::string> atom_refs = structure.atom_refs();
    check(atom_refs.size() == 2, "structure atom ref count");
    check(atom_refs[0] == "elements/hydrogen.atom", "structure first atom ref");
    check(atom_refs[1] == "elements/oxygen.atom", "structure second atom ref");

    Document material_document = parse_document(kMaterial);
    MaterialDefinition material = read_material(material_document);
    check(material.identity.id == "material.gold", "material id");
    check(material.identity.category == "Metal", "material category");
    std::vector<std::string> structure_refs = material.structure_refs();
    check(structure_refs.size() == 1, "material structure ref count");
    check(structure_refs[0] == "structures/gold_crystal.structure", "material structure ref");
    std::optional<Quantity> density = material.property("Density");
    check(density.has_value() && std::fabs(density->value - 19300.0) < 1e-6, "material density value");
    check(density.has_value() && density->unit.symbol == "kg/m^3", "material density unit");

    Document instance_document = parse_document(kInstance);
    MaterialInstance instance = read_instance(instance_document);
    check(instance.instance_id == "instance.poolwater_mix", "instance id");
    check(instance.definition_ref == "materials/water.material", "instance definition ref");
    check(instance.components.size() == 1, "instance component count");
    check(instance.components.size() == 1 && instance.components[0].material_ref == "materials/sodium_chloride.material",
          "instance component ref");

    Document appearance_document = parse_document(kAppearance);
    MaterialDefinition skin = read_material(appearance_document);
    check(skin.appearance.is_map(), "material appearance captured");
    check(skin.contact.is_map(), "material contact captured");
    check(skin.contact_pairs.is_list() && skin.contact_pairs.items().size() == 1, "material contact pairs captured");
    check(skin.extra.is_map() && skin.extra.field("ExtraSection") != nullptr, "unknown section preserved");

    DocumentWriter writer(DocumentType::Material);
    writer.set_identity("material.written", "Written");
    Value appearance = Value::map();
    appearance.set_field("Roughness", Value::number(0.25));
    writer.set_appearance(appearance);
    std::string written = writer.text();
    Document reparsed = parse_document(written);
    MaterialDefinition written_material = read_material(reparsed);
    check(written_material.identity.id == "material.written", "writer identity round-trip");
    check(written_material.appearance.is_map() && written_material.appearance.field("Roughness") != nullptr,
          "writer appearance round-trip");

    DocumentResult ok_result = try_parse_document(kMaterial);
    check(ok_result.has_value(), "try_parse_document success");
    DocumentResult bad_result = try_parse_document("ATOM\n  bad\n");
    check(!bad_result.has_value(), "try_parse_document failure");
    check(!bad_result.has_value() && bad_result.error().line == 2, "try_parse_document error line");

    bool syntax_error = false;
    try {
        parse_document("ATOM\n  bad\n");
    } catch (const ParseError&) {
        syntax_error = true;
    }
    check(syntax_error, "indented keyword rejected");

    if (argc > 1) {
        ResourceLibrary library({argv[1]});
        library.index();
        check(library.size() > 0, "library indexed");
        const Document* gold = library.load("elements/gold.atom");
        check(gold != nullptr, "library load by path");
        check(gold != nullptr && !library.resource_id(*gold).empty(), "library resource id");
        const Document* by_id = library.load(gold != nullptr ? library.resource_id(*gold) : std::string());
        check(by_id == gold, "library load by id returns same document");
    }

    if (failures == 0) {
        std::cout << "all checks passed\n";
        return 0;
    }
    std::cout << failures << " check(s) failed\n";
    return 1;
}
