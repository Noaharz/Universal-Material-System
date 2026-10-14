#include "ums/reader.hpp"

#include <algorithm>
#include <cctype>

namespace ums {

namespace {

std::string string_field(const Value* value) {
    if (value == nullptr) return std::string();
    if (value->is_string()) return value->string_value;
    if (value->is_null()) return std::string();
    return value->scalar_text();
}

Value as_map(const Value& value) {
    return value.is_map() ? value : Value::map();
}

Value as_map(const Value* value) {
    return value == nullptr ? Value::map() : as_map(*value);
}

Value as_list(const Value& value) {
    return value.is_list() ? value : Value::list({});
}

Value as_list(const Value* value) {
    return value == nullptr ? Value::list({}) : as_list(*value);
}

std::optional<Quantity> scalar_quantity(const Value* value) {
    if (value == nullptr) return std::nullopt;
    if (value->is_string()) return try_quantity(value->string_value);
    if (value->is_int() || value->is_float()) {
        return Quantity{value->as_double(), dimensionless_unit()};
    }
    return std::nullopt;
}

void push_unique(std::vector<std::string>& refs, const std::string& ref) {
    if (ref.empty()) return;
    if (std::find(refs.begin(), refs.end(), ref) == refs.end()) refs.push_back(ref);
}

Value collect_extra(const Value& sections, const std::vector<std::string>& known) {
    Value extra = Value::map();
    if (!sections.is_map()) return extra;
    for (const auto& entry : sections.fields()) {
        if (std::find(known.begin(), known.end(), entry.first) != known.end()) continue;
        extra.set_field(entry.first, entry.second);
    }
    return extra;
}

Value optional_section(const Value& sections, const std::string& key) {
    const Value* value = section(sections, key);
    return value != nullptr ? *value : Value::null();
}

std::string canonical_structure_type(const std::string& raw) {
    static const char* types[] = {"Molecular", "Crystal", "Ionic", "Polymer",
                                  "Network",   "Amorphous", "Porous", "Composite"};
    std::string lowered;
    lowered.reserve(raw.size());
    for (char ch : raw) lowered.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
    for (const char* type : types) {
        std::string candidate;
        candidate.reserve(std::char_traits<char>::length(type));
        for (const char* p = type; *p != '\0'; ++p) {
            candidate.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(*p))));
        }
        if (candidate == lowered) return type;
    }
    return "Custom";
}

}  // namespace

const Value* section(const Value& sections, const std::string& key) {
    if (!sections.is_map()) return nullptr;
    return sections.field(key);
}

Identity read_identity(const Value& sections) {
    Identity identity;
    const Value* identity_section = section(sections, "Identity");
    if (identity_section != nullptr && identity_section->is_map()) {
        identity.id = string_field(identity_section->field("Id"));
        if (identity.id.empty()) identity.id = string_field(identity_section->field("ResourceId"));
        identity.name = string_field(identity_section->field("Name"));
        identity.category = string_field(identity_section->field("Category"));
    }

    const Value* version = section(sections, "Version");
    if (version == nullptr) version = identity_section != nullptr ? identity_section->field("Version") : nullptr;
    if (version != nullptr && version->is_number()) identity.version = static_cast<int>(version->as_int(1));
    return identity;
}

std::optional<Quantity> AtomDefinition::property(const std::string& name) const {
    return scalar_quantity(properties.field(name));
}

std::vector<std::string> StructureDefinition::atom_refs() const {
    std::vector<std::string> refs;
    if (composition.is_list()) {
        for (const auto& entry : composition.items()) {
            if (!entry.is_map()) continue;
            std::string ref = string_field(entry.field("AtomRef"));
            if (ref.empty()) ref = string_field(entry.field("Ref"));
            push_unique(refs, ref);
        }
    }
    const Value* atoms = topology.is_map() ? topology.field("Atoms") : nullptr;
    if (atoms != nullptr && atoms->is_list()) {
        for (const auto& atom : atoms->items()) {
            if (atom.is_map()) push_unique(refs, string_field(atom.field("Type")));
        }
    }
    const Value* declared = references.is_map() ? references.field("AtomDefinitions") : nullptr;
    if (declared != nullptr && declared->is_list()) {
        for (const auto& ref : declared->items()) push_unique(refs, string_field(&ref));
    }
    return refs;
}

std::vector<std::string> MaterialDefinition::structure_refs() const {
    std::vector<std::string> refs;
    if (structures.is_list()) {
        for (const auto& entry : structures.items()) {
            if (entry.is_string()) {
                push_unique(refs, entry.string_value);
            } else if (entry.is_map()) {
                std::string ref = string_field(entry.field("StructureRef"));
                if (ref.empty()) ref = string_field(entry.field("Ref"));
                if (ref.empty()) ref = string_field(entry.field("Structure"));
                push_unique(refs, ref);
            }
        }
    }
    const Value* declared = references.is_map() ? references.field("Structures") : nullptr;
    if (declared != nullptr && declared->is_list()) {
        for (const auto& ref : declared->items()) push_unique(refs, string_field(&ref));
    }
    return refs;
}

std::optional<Quantity> MaterialDefinition::property(const std::string& name) const {
    return scalar_quantity(properties.field(name));
}

AtomDefinition read_atom(const Document& document) {
    const Value& sections = document.sections;
    AtomDefinition atom;
    atom.identity = read_identity(sections);
    const Value* identity_section = section(sections, "Identity");
    if (identity_section != nullptr && identity_section->is_map()) {
        atom.symbol = string_field(identity_section->field("Symbol"));
        const Value* number = identity_section->field("AtomicNumber");
        if (number != nullptr && number->is_number()) atom.atomic_number = static_cast<int>(number->as_int());
    }
    atom.properties = as_map(section(sections, "Properties"));
    atom.electronic = as_map(section(sections, "Electronic"));
    atom.nuclear = as_map(section(sections, "Nuclear"));
    atom.physical = as_map(section(sections, "Physical"));
    atom.models = as_map(section(sections, "Models"));
    atom.references = as_map(section(sections, "References"));
    atom.extra = collect_extra(sections, {"Version", "Identity", "Properties", "Electronic", "Nuclear", "Physical",
                                          "Models", "References"});
    atom.source_path = document.path;
    return atom;
}

StructureDefinition read_structure(const Document& document) {
    const Value& sections = document.sections;
    StructureDefinition structure;
    structure.identity = read_identity(sections);
    const Value* identity_section = section(sections, "Identity");
    if (identity_section != nullptr && identity_section->is_map()) {
        std::string type = string_field(identity_section->field("StructureType"));
        if (!type.empty()) structure.structure_type = canonical_structure_type(type);
    }
    const Value* composition = section(sections, "Composition");
    if (composition != nullptr && composition->is_map()) {
        structure.composition = Value::list({*composition});
    } else {
        structure.composition = as_list(composition);
    }
    structure.topology = as_map(section(sections, "Topology"));
    structure.geometry = as_map(section(sections, "Geometry"));
    structure.crystal = as_map(section(sections, "Crystal"));
    structure.periodicity = as_map(section(sections, "Periodicity"));
    structure.models = as_map(section(sections, "Models"));
    structure.references = as_map(section(sections, "References"));
    structure.substructures = as_list(section(sections, "Substructures"));
    structure.extra = collect_extra(sections, {"Version", "Identity", "Composition", "Topology", "Geometry",
                                               "Crystal", "Periodicity", "Models", "References", "Substructures"});
    structure.source_path = document.path;
    return structure;
}

MaterialDefinition read_material(const Document& document) {
    const Value& sections = document.sections;
    MaterialDefinition material;
    material.identity = read_identity(sections);
    if (material.identity.category.empty()) {
        const Value* identity_section = section(sections, "Identity");
        if (identity_section != nullptr) material.identity.category = string_field(identity_section->field("Category"));
    }
    material.composition = as_map(section(sections, "Composition"));
    material.structures = as_list(section(sections, "Structures"));
    material.properties = as_map(section(sections, "Properties"));
    material.models = as_map(section(sections, "Models"));
    material.phases = as_map(section(sections, "Phases"));
    material.variants = as_map(section(sections, "Variants"));
    material.composition_profiles = as_map(section(sections, "CompositionProfiles"));
    material.references = as_map(section(sections, "References"));
    material.appearance = optional_section(sections, "Appearance");
    material.contact = optional_section(sections, "Contact");
    material.contact_pairs = optional_section(sections, "ContactPairs");
    material.extra = collect_extra(
        sections, {"Version", "Identity", "Composition", "Structures", "Properties", "Models", "Phases", "Variants",
                   "CompositionProfiles", "References", "Appearance", "Contact", "ContactPairs"});
    material.source_path = document.path;
    return material;
}

MaterialInstance read_instance(const Document& document) {
    const Value& sections = document.sections;
    MaterialInstance instance;

    const Value* identity_section = section(sections, "Identity");
    std::string id = string_field(identity_section != nullptr ? identity_section->field("Id") : nullptr);
    std::string name = string_field(identity_section != nullptr ? identity_section->field("Name") : nullptr);
    if (name.empty()) name = string_field(section(sections, "Name"));
    if (id.empty()) id = string_field(section(sections, "Id"));
    instance.instance_id = id.empty() ? name : id;
    instance.name = name;

    const Value* definition = section(sections, "Definition");
    if (definition == nullptr) definition = section(sections, "BaseMaterial");
    if (definition == nullptr) definition = section(sections, "Material");
    if (definition != nullptr && definition->is_map()) {
        std::string ref = string_field(definition->field("Ref"));
        if (ref.empty()) ref = string_field(definition->field("Definition"));
        instance.definition_ref = ref;
    } else {
        instance.definition_ref = string_field(definition);
    }

    instance.variant = string_field(section(sections, "Variant"));

    const Value* components = section(sections, "Components");
    if (components != nullptr && components->is_list()) {
        for (const auto& entry : components->items()) {
            if (!entry.is_map()) continue;
            MixComponent component;
            component.material_ref = string_field(entry.field("MaterialRef"));
            if (component.material_ref.empty()) component.material_ref = string_field(entry.field("Ref"));
            component.concentration = scalar_quantity(entry.field("Concentration"));
            component.role = string_field(entry.field("Role"));
            instance.components.push_back(std::move(component));
        }
    }

    instance.state = as_map(section(sections, "State"));
    instance.parameters = as_map(section(sections, "Parameters"));
    instance.appearance = optional_section(sections, "Appearance");
    instance.contact = optional_section(sections, "Contact");
    instance.extra = collect_extra(
        sections, {"Version", "Identity", "Id", "Name", "Definition", "BaseMaterial", "Material", "Variant",
                   "Components", "State", "Parameters", "Appearance", "Contact"});
    instance.source_path = document.path;
    return instance;
}

}  // namespace ums
