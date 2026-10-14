#pragma once

#include <optional>
#include <string>
#include <vector>

#include "ums/parser.hpp"
#include "ums/units.hpp"
#include "ums/value.hpp"

namespace ums {

struct Identity {
    std::string id;
    std::string name;
    std::string category;
    int version = 1;
};

const Value* section(const Value& sections, const std::string& key);

Identity read_identity(const Value& sections);

struct AtomDefinition {
    Identity identity;
    std::string symbol;
    int atomic_number = 0;
    Value properties;
    Value electronic;
    Value nuclear;
    Value physical;
    Value models;
    Value references;
    std::string source_path;

    std::optional<Quantity> property(const std::string& name) const;
};

struct StructureDefinition {
    Identity identity;
    std::string structure_type = "Custom";
    Value composition;
    Value topology;
    Value geometry;
    Value crystal;
    Value periodicity;
    Value models;
    Value references;
    Value substructures;
    std::string source_path;

    std::vector<std::string> atom_refs() const;
};

struct MaterialDefinition {
    Identity identity;
    Value composition;
    Value structures;
    Value properties;
    Value models;
    Value phases;
    Value variants;
    Value composition_profiles;
    Value references;
    std::string source_path;

    std::vector<std::string> structure_refs() const;
    std::optional<Quantity> property(const std::string& name) const;
};

struct MixComponent {
    std::string material_ref;
    std::optional<Quantity> concentration;
    std::string role;
};

struct MaterialInstance {
    std::string instance_id;
    std::string definition_ref;
    std::string name;
    std::string variant;
    Value state;
    Value parameters;
    std::vector<MixComponent> components;
    std::string source_path;
};

AtomDefinition read_atom(const Document& document);
StructureDefinition read_structure(const Document& document);
MaterialDefinition read_material(const Document& document);
MaterialInstance read_instance(const Document& document);

}  // namespace ums
