#pragma once

#include <array>
#include <optional>
#include <string>

namespace ums {

struct Dimension {
    std::array<int, 7> exponents{0, 0, 0, 0, 0, 0, 0};

    static Dimension base(int index);
    bool dimensionless() const;
    Dimension operator*(const Dimension& other) const;
    Dimension operator/(const Dimension& other) const;
    Dimension pow(int power) const;
    bool operator==(const Dimension& other) const { return exponents == other.exponents; }
    bool operator!=(const Dimension& other) const { return !(*this == other); }
    std::string to_string() const;
};

struct Unit {
    std::string symbol;
    Dimension dimension{};
    double scale = 1.0;

    bool is_dimensionless() const;
    double to_si(double value) const { return value * scale; }
    double from_si(double value) const { return value / scale; }
    Unit operator*(const Unit& other) const;
    Unit operator/(const Unit& other) const;
    Unit pow(int power) const;
    bool compatible(const Unit& other) const { return dimension == other.dimension; }
    bool operator==(const Unit& other) const;
};

struct Quantity {
    double value = 0.0;
    Unit unit;

    double si_value() const { return unit.to_si(value); }
    double as(const Unit& target) const;
    std::string to_string() const;
};

const Unit& dimensionless_unit();

std::string format_general(double value);

const Unit& get_unit(const std::string& name);
void register_unit(const std::string& name, const Unit& unit);
Unit parse_unit(const std::string& expression);
Quantity parse_quantity(const std::string& text);
std::optional<Quantity> try_quantity(const std::string& text);
bool is_number_token(const std::string& text);

}  // namespace ums
