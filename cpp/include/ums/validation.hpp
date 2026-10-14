#pragma once

#include <functional>
#include <optional>
#include <string>
#include <vector>

#include "ums/parser.hpp"
#include "ums/units.hpp"
#include "ums/value.hpp"

namespace ums {

enum class Severity { Error, Warning, Info };

std::string to_string(Severity severity);

struct Issue {
    std::string code;
    std::string message;
    Severity severity = Severity::Error;
    std::string path;
};

class ValidationReport {
public:
    std::string subject;
    std::vector<Issue> issues;

    bool is_valid() const;
    void add(const std::string& code, const std::string& message, Severity severity = Severity::Error,
             const std::string& path = std::string());
};

using ReferenceChecker = std::function<bool(const std::string&)>;

class Validator {
public:
    explicit Validator(ReferenceChecker reference_checker = ReferenceChecker());

    ValidationReport validate_atom(const Document& document) const;
    ValidationReport validate_structure(const Document& document) const;
    ValidationReport validate_material(const Document& document) const;
    ValidationReport validate(const Document& document) const;

private:
    void check_reference(ValidationReport& report, const std::string& ref, const std::string& path) const;
    void check_id(ValidationReport& report, const std::string& resource_id, const std::string& kind) const;
    void validate_quantity(ValidationReport& report, const std::optional<Quantity>& value, const std::string& path,
                           const std::array<int, 7>* expected) const;

    ReferenceChecker reference_checker_;
};

const std::array<int, 7> kDimMass{1, 0, 0, 0, 0, 0, 0};
const std::array<int, 7> kDimLength{0, 1, 0, 0, 0, 0, 0};

}  // namespace ums
