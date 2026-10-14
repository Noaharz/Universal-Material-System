#include "ums/validation.hpp"

#include <algorithm>
#include <array>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <map>
#include <string>

#include "ums/errors.hpp"
#include "ums/reader.hpp"

namespace ums {

namespace {

bool valid_id(const std::string& value) {
    if (value.empty()) return false;
    char first = value[0];
    bool first_ok = std::isalnum(static_cast<unsigned char>(first)) || first == '_';
    if (!first_ok) return false;
    for (char ch : value) {
        if (std::isalnum(static_cast<unsigned char>(ch)) || ch == '_' || ch == '.' || ch == '-') continue;
        return false;
    }
    return true;
}

std::optional<Quantity> value_to_quantity(const Value& value) {
    if (value.is_string()) return try_quantity(value.string_value);
    if (value.is_int() || value.is_float()) return Quantity{value.as_double(), dimensionless_unit()};
    if (value.is_bool()) return Quantity{value.bool_value ? 1.0 : 0.0, dimensionless_unit()};
    return std::nullopt;
}

std::optional<Quantity> field_quantity(const Value& map, const std::string& key) {
    if (!map.is_map()) return std::nullopt;
    const Value* field = map.field(key);
    if (field == nullptr) return std::nullopt;
    return value_to_quantity(*field);
}

std::string py_repr(const Value& value) {
    switch (value.type) {
        case Value::Type::Null:
            return "None";
        case Value::Type::Bool:
            return value.bool_value ? "True" : "False";
        case Value::Type::Int:
            return std::to_string(value.int_value);
        case Value::Type::Float: {
            char buffer[64];
            std::snprintf(buffer, sizeof(buffer), "%g", value.float_value);
            std::string text(buffer);
            if (text.find('.') == std::string::npos && text.find('e') == std::string::npos &&
                text.find('E') == std::string::npos && text.find("inf") == std::string::npos &&
                text.find("nan") == std::string::npos) {
                text += ".0";
            }
            return text;
        }
        case Value::Type::String:
            return "'" + value.string_value + "'";
        case Value::Type::List: {
            std::string text = "[";
            for (std::size_t i = 0; i < value.items().size(); ++i) {
                if (i != 0) text += ", ";
                text += py_repr(value.items()[i]);
            }
            return text + "]";
        }
        case Value::Type::Map: {
            std::string text = "{";
            bool first = true;
            for (const auto& entry : value.fields()) {
                if (!first) text += ", ";
                first = false;
                text += "'" + entry.first + "': " + py_repr(entry.second);
            }
            return text + "}";
        }
    }
    return std::string();
}

std::string dimension_name(const std::array<int, 7>& exponents) {
    static const std::map<std::array<int, 7>, std::string> names = {
        {std::array<int, 7>{0, 0, 0, 0, 0, 0, 0}, "dimensionless"},
        {std::array<int, 7>{1, 0, 0, 0, 0, 0, 0}, "mass"},
        {std::array<int, 7>{0, 1, 0, 0, 0, 0, 0}, "length"},
        {std::array<int, 7>{0, 0, 1, 0, 0, 0, 0}, "time"},
        {std::array<int, 7>{0, 0, 0, 1, 0, 0, 0}, "temperature"},
        {std::array<int, 7>{0, 0, 0, 0, 0, 1, 0}, "amount"},
        {std::array<int, 7>{1, 2, -2, 0, 0, 0, 0}, "energy"},
        {std::array<int, 7>{1, -1, -2, 0, 0, 0, 0}, "pressure"},
        {std::array<int, 7>{1, 2, -3, 0, 0, 0, 0}, "power"},
        {std::array<int, 7>{1, -3, 0, 0, 0, 0, 0}, "density"},
        {std::array<int, 7>{1, 1, -3, -1, 0, 0, 0}, "thermal conductivity"},
        {std::array<int, 7>{0, 2, -2, -1, 0, 0, 0}, "specific heat capacity"},
        {std::array<int, 7>{1, -1, -1, 0, 0, 0, 0}, "dynamic viscosity"},
        {std::array<int, 7>{-1, -3, 3, 0, 2, 0, 0}, "electrical conductivity"},
        {std::array<int, 7>{0, 3, 0, 0, 0, 0, 0}, "volume"},
    };
    auto it = names.find(exponents);
    if (it != names.end()) return it->second;

    static const char* base[7] = {"mass", "length", "time", "temperature", "current", "amount", "luminosity"};
    std::string text;
    for (std::size_t i = 0; i < exponents.size(); ++i) {
        if (exponents[i] == 0) continue;
        if (!text.empty()) text += " * ";
        text += base[i];
        text += "^" + std::to_string(exponents[i]);
    }
    return text.empty() ? "dimensionless" : text;
}

const std::map<std::string, std::array<int, 7>>& material_dimensions() {
    static const std::map<std::string, std::array<int, 7>> table = {
        {"Density", {1, -3, 0, 0, 0, 0, 0}},
        {"ThermalConductivity", {1, 1, -3, -1, 0, 0, 0}},
        {"HeatCapacity", {0, 2, -2, -1, 0, 0, 0}},
        {"Viscosity", {1, -1, -1, 0, 0, 0, 0}},
        {"YoungsModulus", {1, -1, -2, 0, 0, 0, 0}},
        {"ElectricalConductivity", {-1, -3, 3, 0, 2, 0, 0}},
    };
    return table;
}

std::string string_field(const Value& map, const std::string& key) {
    if (!map.is_map()) return std::string();
    const Value* value = map.field(key);
    return value != nullptr && value->is_string() ? value->string_value : std::string();
}

}  // namespace

std::string to_string(Severity severity) {
    switch (severity) {
        case Severity::Error:
            return "error";
        case Severity::Warning:
            return "warning";
        case Severity::Info:
            return "info";
    }
    return "error";
}

bool ValidationReport::is_valid() const {
    for (const auto& issue : issues) {
        if (issue.severity == Severity::Error) return false;
    }
    return true;
}

void ValidationReport::add(const std::string& code, const std::string& message, Severity severity,
                           const std::string& path) {
    issues.push_back(Issue{code, message, severity, path});
}

Validator::Validator(ReferenceChecker reference_checker) : reference_checker_(std::move(reference_checker)) {}

void Validator::check_reference(ValidationReport& report, const std::string& ref, const std::string& path) const {
    if (ref.empty()) {
        report.add("REF_EMPTY", "empty resource reference", Severity::Error, path);
        return;
    }
    if (ref.find('\\') != std::string::npos) {
        report.add("REF_BACKSLASH", "resource path must use '/' not '\\': '" + ref + "'", Severity::Error, path);
    }
    if (ref[0] == '/' || (ref.size() > 1 && ref[1] == ':')) {
        report.add("REF_ABSOLUTE", "resource path must be relative: '" + ref + "'", Severity::Error, path);
    }
    if (reference_checker_) {
        if (!reference_checker_(ref)) {
            report.add("REF_UNRESOLVED", "reference cannot be resolved: '" + ref + "'", Severity::Error, path);
        }
    } else {
        report.add("REF_UNCHECKED", "reference not resolved (no library): '" + ref + "'", Severity::Info, path);
    }
}

void Validator::check_id(ValidationReport& report, const std::string& resource_id, const std::string& kind) const {
    if (resource_id.empty()) {
        report.add("ID_MISSING", kind + " Id is required", Severity::Error, "Identity.Id");
    } else if (!valid_id(resource_id)) {
        report.add("ID_INVALID", kind + " Id has invalid characters: '" + resource_id + "'", Severity::Error,
                   "Identity.Id");
    }
}

void Validator::validate_quantity(ValidationReport& report, const std::optional<Quantity>& value,
                                  const std::string& path, const std::array<int, 7>* expected) const {
    if (!value.has_value()) return;
    if (expected != nullptr && value->unit.dimension.exponents != *expected) {
        report.add("DIMENSION_MISMATCH",
                   path + " expects " + dimension_name(*expected) + " but got '" + value->unit.symbol + "' (" +
                       dimension_name(value->unit.dimension.exponents) + ")",
                   Severity::Error, path);
    }
}

ValidationReport Validator::validate_atom(const Document& document) const {
    AtomDefinition atom = read_atom(document);
    std::string subject = !atom.identity.id.empty() ? atom.identity.id
                          : !atom.identity.name.empty() ? atom.identity.name
                                                        : "<atom>";
    ValidationReport report;
    report.subject = subject;
    check_id(report, atom.identity.id, "atom");
    if (atom.identity.version < 1) {
        report.add("VERSION_INVALID", "version must be >= 1", Severity::Error, "Version");
    }
    if (atom.identity.name.empty()) {
        report.add("NAME_MISSING", "atom Name is required", Severity::Warning, "Identity.Name");
    }
    const Value* identity_section = section(document.sections, "Identity");
    bool has_z = false;
    int z = 0;
    if (identity_section != nullptr && identity_section->is_map()) {
        const Value* number = identity_section->field("AtomicNumber");
        if (number != nullptr && number->is_number()) {
            z = static_cast<int>(number->as_int());
            has_z = true;
        }
    }
    if (has_z && z <= 0) {
        report.add("Z_INVALID", "AtomicNumber must be positive, got " + std::to_string(z), Severity::Error,
                   "Identity.AtomicNumber");
    }
    validate_quantity(report, field_quantity(atom.properties, "AtomicMass"), "Properties.AtomicMass", &kDimMass);
    for (const char* key : {"AtomicRadius", "CovalentRadius"}) {
        validate_quantity(report, field_quantity(atom.properties, key), std::string("Properties.") + key, &kDimLength);
    }
    static const std::array<int, 7> energy{1, 2, -2, 0, 0, 0, 0};
    validate_quantity(report, field_quantity(atom.properties, "IonizationEnergy"), "Properties.IonizationEnergy",
                      &energy);
    validate_quantity(report, field_quantity(atom.properties, "Electronegativity"), "Properties.Electronegativity",
                      nullptr);

    if (atom.references.is_map()) {
        const Value* sources = atom.references.field("DataSource");
        std::vector<Value> items;
        if (sources != nullptr && sources->is_list()) {
            items = sources->items();
        } else if (sources != nullptr) {
            items.push_back(*sources);
        }
        for (const auto& ref : items) {
            if (ref.is_null()) continue;
            std::string text = ref.scalar_text();
            if (!text.empty()) {
                report.add("REF_EXTERNAL", "external data source: " + text, Severity::Info, "References.DataSource");
            }
        }
    }
    return report;
}

ValidationReport Validator::validate_structure(const Document& document) const {
    StructureDefinition structure = read_structure(document);
    std::string subject = !structure.identity.id.empty() ? structure.identity.id
                          : !structure.identity.name.empty() ? structure.identity.name
                                                            : "<structure>";
    ValidationReport report;
    report.subject = subject;
    check_id(report, structure.identity.id, "structure");
    if (structure.identity.version < 1) {
        report.add("VERSION_INVALID", "version must be >= 1", Severity::Error, "Version");
    }
    if (structure.structure_type == "Custom" && structure.crystal.fields().empty() &&
        structure.topology.fields().empty()) {
        report.add("TYPE_AMBIGUOUS",
                   "StructureType is Custom or missing but no specific structure sections are present",
                   Severity::Warning, "Identity.StructureType");
    }

    const Value* atoms = structure.topology.is_map() ? structure.topology.field("Atoms") : nullptr;
    std::vector<std::string> atom_ids;
    if (atoms != nullptr && atoms->is_list()) {
        int idx = 0;
        for (const auto& atom : atoms->items()) {
            std::string index = "Topology.Atoms[" + std::to_string(idx) + "]";
            ++idx;
            if (!atom.is_map()) {
                report.add("ATOM_ENTRY_INVALID", "topology atom entries must be mappings", Severity::Error, index);
                continue;
            }
            std::string local_id = string_field(atom, "Id");
            if (local_id.empty()) {
                report.add("ATOM_LOCAL_ID_MISSING", "topology atom requires a local Id", Severity::Error, index);
            } else if (std::find(atom_ids.begin(), atom_ids.end(), local_id) != atom_ids.end()) {
                report.add("ATOM_LOCAL_ID_DUP", "duplicate topology atom Id: '" + local_id + "'", Severity::Error,
                           index);
            } else {
                atom_ids.push_back(local_id);
            }
            if (string_field(atom, "Type").empty()) {
                report.add("ATOM_TYPE_MISSING", "topology atom '" + local_id + "' has no Type reference",
                           Severity::Error, index);
            }
        }
    }

    const Value* bonds = structure.topology.is_map() ? structure.topology.field("Bonds") : nullptr;
    if (bonds != nullptr && bonds->is_list()) {
        int idx = 0;
        for (const auto& bond : bonds->items()) {
            std::string index = "Topology.Bonds[" + std::to_string(idx) + "]";
            ++idx;
            if (!bond.is_map()) {
                report.add("BOND_ENTRY_INVALID", "bond entries must be mappings", Severity::Error, index);
                continue;
            }
            for (const char* endpoint : {"From", "To"}) {
                std::string value = string_field(bond, endpoint);
                if (value.empty()) {
                    report.add("BOND_ENDPOINT_MISSING", std::string("bond requires ") + endpoint, Severity::Error,
                               index);
                } else if (!atom_ids.empty() &&
                           std::find(atom_ids.begin(), atom_ids.end(), value) == atom_ids.end()) {
                    report.add("BOND_ENDPOINT_UNKNOWN",
                               "bond endpoint '" + value + "' is not a declared topology atom", Severity::Error,
                               index + "." + endpoint);
                }
            }
        }
    }

    for (const auto& ref : structure.atom_refs()) {
        check_reference(report, ref, "Composition.AtomRef");
    }
    if (structure.references.is_map()) {
        const Value* subs = structure.references.field("Substructures");
        if (subs != nullptr && subs->is_list()) {
            for (const auto& ref : subs->items()) check_reference(report, ref.scalar_text(), "References.Substructures");
        }
    }

    if (!structure.periodicity.fields().empty()) {
        const Value* dims = structure.periodicity.field("Dimensions");
        if (dims != nullptr && !dims->is_int() && !dims->is_bool()) {
            report.add("PERIODICITY_DIMENSIONS", "Periodicity.Dimensions must be an integer", Severity::Error,
                       "Periodicity.Dimensions");
        }
        const Value* axes = structure.periodicity.field("PeriodicAxes");
        if (axes != nullptr) {
            bool ok = axes->is_list();
            if (ok) {
                for (const auto& item : axes->items()) {
                    if (!item.is_bool()) {
                        ok = false;
                        break;
                    }
                }
            }
            if (!ok) {
                report.add("PERIODICITY_AXES", "PeriodicAxes must be a list of booleans", Severity::Error,
                           "Periodicity.PeriodicAxes");
            }
        }
    }

    validate_quantity(report, field_quantity(structure.crystal, "LatticeParameter"), "Crystal.LatticeParameter",
                      &kDimLength);
    validate_quantity(report, field_quantity(structure.geometry, "BondAngle"), "Geometry.BondAngle", nullptr);
    return report;
}

ValidationReport Validator::validate_material(const Document& document) const {
    MaterialDefinition material = read_material(document);
    std::string subject = !material.identity.id.empty() ? material.identity.id
                          : !material.identity.name.empty() ? material.identity.name
                                                          : "<material>";
    ValidationReport report;
    report.subject = subject;
    check_id(report, material.identity.id, "material");
    if (material.identity.version < 1) {
        report.add("VERSION_INVALID", "version must be >= 1", Severity::Error, "Version");
    }
    if (material.identity.name.empty()) {
        report.add("NAME_MISSING", "material Name is required", Severity::Warning, "Identity.Name");
    }
    std::vector<std::string> refs = material.structure_refs();
    for (const auto& ref : refs) check_reference(report, ref, "Structures");

    if (material.properties.is_map()) {
        for (const auto& entry : material.properties.fields()) {
            if (!entry.second.is_map()) continue;
            if (string_field(entry.second, "Model").empty()) {
                report.add("PROPERTY_MODEL_MISSING",
                           "property '" + entry.first + "' has a mapping but no Model key", Severity::Error,
                           "Properties." + entry.first);
            }
        }
    }

    for (const auto& entry : material_dimensions()) {
        validate_quantity(report, field_quantity(material.properties, entry.first), "Properties." + entry.first,
                          &entry.second);
    }

    if (material.composition_profiles.is_map()) {
        for (const auto& entry : material.composition_profiles.fields()) {
            const Value& profile = entry.second;
            if (profile.is_map() && profile.fields().empty()) {
                report.add("PROFILE_EMPTY", "composition profile '" + entry.first + "' is empty", Severity::Warning,
                           "CompositionProfiles." + entry.first);
            }
        }
    }

    bool has_composition = material.composition.is_map() ? !material.composition.fields().empty()
                                                         : !material.composition.is_null();
    bool has_profiles = material.composition_profiles.is_map() && !material.composition_profiles.fields().empty();
    if (!has_composition && !has_profiles && refs.empty()) {
        report.add("COMPOSITION_MISSING",
                   "material has neither composition, composition profiles nor structure references", Severity::Info,
                   "Composition");
    }
    return report;
}

ValidationReport Validator::validate(const Document& document) const {
    switch (document.type) {
        case DocumentType::Atom:
            return validate_atom(document);
        case DocumentType::Structure:
            return validate_structure(document);
        case DocumentType::Material:
            return validate_material(document);
        case DocumentType::Instance:
            throw ValidationError("cannot validate object of type MaterialInstance");
    }
    throw ValidationError("cannot validate unknown document type");
}

}  // namespace ums
