#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>
#include <vector>

#include "ums/errors.hpp"
#include "ums/fileio.hpp"
#include "ums/library.hpp"
#include "ums/parser.hpp"
#include "ums/registry.hpp"
#include "ums/serializer.hpp"
#include "ums/units.hpp"
#include "ums/validation.hpp"

namespace {

void print_usage() {
    std::cerr << "usage: umsconf <command> [options] <target>\n"
                 "\n"
                 "commands:\n"
                 "  canonical   parse then serialize a document deterministically\n"
                 "  parse       parse a document and report success or an error\n"
                 "  try-parse   non-throwing parse; prints OK or a diagnostic\n"
                 "  validate    run the validation rules and print the report\n"
                 "  resolve     report whether a reference can be resolved\n"
                 "  unit        parse a unit expression and print its dimension\n"
                 "  quantity    parse a quantity and print its value and unit\n"
                 "\n"
                 "options:\n"
                 "  --lib DIR   add a library search path (repeatable)\n";
}

std::string join_dimension(const ums::Dimension& dimension) {
    std::string text;
    for (std::size_t i = 0; i < dimension.exponents.size(); ++i) {
        if (i != 0) text += ",";
        text += std::to_string(dimension.exponents[i]);
    }
    return text;
}

std::string double_text(double value) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.17g", value);
    return std::string(buffer);
}

}  // namespace

int main(int argc, char** argv) {
    using namespace ums;

    std::string command;
    std::string target;
    std::vector<std::string> libraries;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--lib") {
            if (i + 1 >= argc) {
                std::cerr << "error: --lib requires a directory\n";
                return 2;
            }
            libraries.push_back(argv[++i]);
        } else if (arg == "-h" || arg == "--help") {
            print_usage();
            return 0;
        } else if (command.empty()) {
            command = arg;
        } else {
            target = arg;
        }
    }

    if (command.empty()) {
        print_usage();
        return 2;
    }

    if (command == "unit" || command == "quantity") {
        try {
            if (command == "unit") {
                Unit unit = parse_unit(target);
                std::cout << "symbol\t" << unit.symbol << "\tscale\t" << double_text(unit.scale) << "\tdim\t"
                          << join_dimension(unit.dimension) << "\n";
            } else {
                Quantity quantity = parse_quantity(target);
                std::cout << "value\t" << double_text(quantity.value) << "\tsymbol\t" << quantity.unit.symbol
                          << "\tdim\t" << join_dimension(quantity.unit.dimension) << "\n";
            }
        } catch (const std::exception& error) {
            std::cout << "ERROR\t" << error.what() << "\n";
        }
        return 0;
    }

    Document document;
    bool have_document = false;
    try {
        if (command == "try-parse") {
            std::string text = read_file(target);
            DocumentResult result = try_parse_buffer(text.data(), text.size(), target);
            if (result.has_value()) {
                std::cout << "OK\t" << to_string(result->type) << "\n";
                return 0;
            }
            const Diagnostic& diagnostic = result.error();
            std::cout << "DIAG\t" << diagnostic.code << "\t" << diagnostic.line << "\t" << diagnostic.column << "\t"
                      << diagnostic.path << "\n";
            return 1;
        }
        if (!libraries.empty()) {
            ResourceLibrary library(libraries);
            library.index();
            if (command == "resolve") {
                std::cout << (library.has(target) ? "true" : "false") << "\n";
                return 0;
            }
            const Document* loaded = library.load(target);
            if (loaded == nullptr) {
                std::cout << "ERROR\tresource not found: " << target << "\n";
                return 1;
            }
            document = *loaded;
            have_document = true;
        } else {
            document = parse_file(target);
            have_document = true;
        }
    } catch (const std::exception& error) {
        std::cout << "ERROR\t" << error.what() << "\n";
        return 1;
    }

    if (!have_document) return 1;

    if (command == "resolve") {
        std::cout << "true\n";
        return 0;
    }

    if (command == "parse") {
        std::cout << "OK\t" << to_string(document.type) << "\n";
        return 0;
    }

    if (command == "canonical") {
        std::cout << serialize_document(document.type, document.sections);
        return 0;
    }

    if (command == "validate") {
        try {
            Validator validator;
            ValidationReport report = validator.validate(document);
            std::cout << "subject\t" << report.subject << "\n";
            std::cout << "valid\t" << (report.is_valid() ? "true" : "false") << "\n";
            for (const auto& issue : report.issues) {
                std::cout << "issue\t" << to_string(issue.severity) << "\t" << issue.code << "\t" << issue.path
                          << "\n";
            }
        } catch (const std::exception& error) {
            std::cout << "ERROR\t" << error.what() << "\n";
            return 1;
        }
        return 0;
    }

    std::cerr << "error: unknown command " << command << "\n";
    return 2;
}
