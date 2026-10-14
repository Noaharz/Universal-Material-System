#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "ums/fileio.hpp"
#include "ums/library.hpp"
#include "ums/parser.hpp"
#include "ums/reader.hpp"

namespace {

void print_usage() {
    std::cout << "usage: umsdump [--tree] [--list] [--lib DIR]... <file-or-ref>\n"
                 "\n"
                 "  --tree       dump the raw parsed section tree\n"
                 "  --list       list all indexed resources in the libraries\n"
                 "  --lib DIR    add a library search path (repeatable)\n";
}

std::string quantity_text(const std::optional<ums::Quantity>& quantity) {
    if (!quantity.has_value()) return std::string();
    std::string text = ums::format_general(quantity->value);
    if (!quantity->unit.symbol.empty()) text += " " + quantity->unit.symbol;
    return text;
}

void print_summary(const ums::Document& document) {
    using ums::DocumentType;
    std::cout << "type: " << ums::to_string(document.type) << "\n";

    if (document.type == DocumentType::Atom) {
        ums::AtomDefinition atom = ums::read_atom(document);
        std::cout << "id: " << atom.identity.id << "\n";
        std::cout << "name: " << atom.identity.name << "\n";
        if (!atom.symbol.empty()) std::cout << "symbol: " << atom.symbol << "\n";
        if (atom.atomic_number > 0) std::cout << "atomic_number: " << atom.atomic_number << "\n";
        for (const auto& entry : atom.properties.fields()) {
            std::optional<ums::Quantity> quantity = atom.property(entry.first);
            if (quantity.has_value()) {
                std::cout << "property " << entry.first << " = " << quantity_text(quantity) << "\n";
            }
        }
    } else if (document.type == DocumentType::Structure) {
        ums::StructureDefinition structure = ums::read_structure(document);
        std::cout << "id: " << structure.identity.id << "\n";
        std::cout << "name: " << structure.identity.name << "\n";
        std::cout << "structure_type: " << structure.structure_type << "\n";
        for (const auto& ref : structure.atom_refs()) std::cout << "atom_ref: " << ref << "\n";
    } else if (document.type == DocumentType::Material) {
        ums::MaterialDefinition material = ums::read_material(document);
        std::cout << "id: " << material.identity.id << "\n";
        std::cout << "name: " << material.identity.name << "\n";
        if (!material.identity.category.empty()) std::cout << "category: " << material.identity.category << "\n";
        for (const auto& ref : material.structure_refs()) std::cout << "structure_ref: " << ref << "\n";
        for (const auto& entry : material.properties.fields()) {
            std::optional<ums::Quantity> quantity = material.property(entry.first);
            if (quantity.has_value()) {
                std::cout << "property " << entry.first << " = " << quantity_text(quantity) << "\n";
            } else {
                std::cout << "property " << entry.first << " = " << entry.second.scalar_text() << "\n";
            }
        }
    } else if (document.type == DocumentType::Instance) {
        ums::MaterialInstance instance = ums::read_instance(document);
        std::cout << "id: " << instance.instance_id << "\n";
        std::cout << "name: " << instance.name << "\n";
        if (!instance.definition_ref.empty()) std::cout << "definition: " << instance.definition_ref << "\n";
        if (!instance.variant.empty()) std::cout << "variant: " << instance.variant << "\n";
        for (const auto& component : instance.components) {
            std::cout << "component: " << component.material_ref;
            if (component.concentration.has_value()) std::cout << " @ " << quantity_text(component.concentration);
            std::cout << "\n";
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    bool tree = false;
    bool list = false;
    std::vector<std::string> libraries;
    std::string target;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--tree") {
            tree = true;
        } else if (arg == "--list") {
            list = true;
        } else if (arg == "--lib") {
            if (i + 1 >= argc) {
                std::cerr << "error: --lib requires a directory\n";
                return 2;
            }
            libraries.push_back(argv[++i]);
        } else if (arg == "-h" || arg == "--help") {
            print_usage();
            return 0;
        } else if (!arg.empty() && arg[0] == '-') {
            std::cerr << "error: unknown option " << arg << "\n";
            return 2;
        } else {
            target = arg;
        }
    }

    if (!libraries.empty()) {
        ums::ResourceLibrary library(libraries);
        library.index();
        if (list || target.empty()) {
            std::cout << "resources: " << library.size() << "\n";
            for (const auto& path : library.logical_paths()) {
                const ums::Document* document = library.load(path);
                std::string id = document != nullptr ? library.resource_id(*document) : std::string();
                std::cout << "  " << path << "  [" << id << "]\n";
            }
            if (target.empty()) return 0;
        }
        const ums::Document* document = library.load(target);
        if (document == nullptr) {
            std::cerr << "error: resource not found: " << target << "\n";
            return 1;
        }
        if (tree) {
            document->sections.dump(std::cout);
        } else {
            print_summary(*document);
        }
        return 0;
    }

    if (target.empty()) {
        print_usage();
        return 2;
    }

    try {
        ums::Document document = ums::parse_file(target);
        if (tree) {
            document.sections.dump(std::cout);
        } else {
            print_summary(document);
        }
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << "\n";
        return 1;
    }
    return 0;
}
