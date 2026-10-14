#include <cmath>
#include <iostream>
#include <string>

#include "ums/errors.hpp"
#include "ums/parser.hpp"
#include "ums/reader.hpp"
#include "ums/registry.hpp"
#include "ums/serializer.hpp"
#include "ums/units.hpp"
#include "ums/validation.hpp"

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
    - AtomRef: "elements/gold.atom"
      Count: 2
)";

}  // namespace

int main() {
    using namespace ums;

    Quantity mass = parse_quantity("196.96657 u");
    check(std::fabs(mass.value - 196.96657) < 1e-9, "quantity value");
    check(mass.unit.symbol == "u", "quantity unit symbol");

    Quantity percent = parse_quantity("0.5%");
    check(std::fabs(percent.value - 0.5) < 1e-12, "percent value");
    check(percent.unit.symbol == "%", "percent symbol");

    Unit density = parse_unit("kg/m^3");
    check(density.dimension.exponents == std::array<int, 7>{1, -3, 0, 0, 0, 0, 0}, "density dimension");
    check(density.symbol == "kg/m^3", "density symbol");
    check(std::fabs(density.scale - 1.0) < 1e-12, "density scale");

    Unit kilo = parse_unit("km");
    check(std::fabs(kilo.scale - 1000.0) < 1e-12, "km scale");

    Document atom = parse_document(kAtom);
    std::string canonical = serialize_document(atom.type, atom.sections);
    Document reparsed = parse_document(canonical);
    const Value* identity = section(reparsed.sections, "Identity");
    check(identity != nullptr && identity->field("Id") != nullptr, "round-trip keeps identity");
    check(canonical.find("AtomicMass: 196.96657 u") != std::string::npos, "round-trip keeps quantity text");
    std::string again = serialize_document(reparsed.type, reparsed.sections);
    check(canonical == again, "serialization is stable");

    bool located = false;
    try {
        parse_document("ATOM\n  bad\n");
    } catch (const ParseError& error) {
        located = error.line() == 2 && error.column() == 3;
    }
    check(located, "parse error reports line and column");

    ResourceRegistry registry;
    Document structure_document = parse_document(kStructure);
    registry.add("elements/gold.atom", "elements/gold.atom", parse_document(kAtom));
    registry.add("structures/water.structure", "structures/water.structure", structure_document);
    check(registry.has("element.gold"), "registry resolves by id");
    check(registry.has("elements/gold.atom"), "registry resolves by path");
    check(!registry.has("elements/missing.atom"), "registry reports missing refs");
    auto graph = registry.dependencies("structure.water");
    check(graph.size() == 2, "dependency graph reaches atoms");
    check(registry.missing_references().empty(), "no missing references");

    Validator validator;
    ValidationReport good = validator.validate(atom);
    check(good.is_valid(), "valid atom report");

    Document bad_atom = parse_document("ATOM\n\nIdentity:\n    Name: \"X\"\n");
    ValidationReport bad = validator.validate(bad_atom);
    check(!bad.is_valid(), "invalid atom report");
    bool has_id_issue = false;
    for (const auto& issue : bad.issues) {
        if (issue.code == "ID_MISSING") has_id_issue = true;
    }
    check(has_id_issue, "missing id reported");

    if (failures == 0) {
        std::cout << "all checks passed\n";
        return 0;
    }
    std::cout << failures << " check(s) failed\n";
    return 1;
}
