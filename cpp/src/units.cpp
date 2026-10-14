#include "ums/units.hpp"

#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <unordered_map>
#include <vector>

#include "ums/errors.hpp"

namespace ums {

namespace {

const char* kBaseNames[7] = {"mass", "length", "time", "temperature", "current", "amount", "luminosity"};

Dimension make_dim(int m, int l, int t, int th, int i, int n, int j) {
    Dimension dimension;
    dimension.exponents = {m, l, t, th, i, n, j};
    return dimension;
}

Unit make_unit(const char* symbol, const Dimension& dimension, double scale) {
    Unit unit;
    unit.symbol = symbol;
    unit.dimension = dimension;
    unit.scale = scale;
    return unit;
}

const std::unordered_map<std::string, Unit>& registry() {
    static const std::unordered_map<std::string, Unit> table = [] {
        std::unordered_map<std::string, Unit> map;
        const Dimension mass = make_dim(1, 0, 0, 0, 0, 0, 0);
        const Dimension length = make_dim(0, 1, 0, 0, 0, 0, 0);
        const Dimension time = make_dim(0, 0, 1, 0, 0, 0, 0);
        const Dimension temperature = make_dim(0, 0, 0, 1, 0, 0, 0);
        const Dimension current = make_dim(0, 0, 0, 0, 1, 0, 0);
        const Dimension amount = make_dim(0, 0, 0, 0, 0, 1, 0);
        const Dimension luminosity = make_dim(0, 0, 0, 0, 0, 0, 1);
        const Dimension dimensionless;

        map["kg"] = make_unit("kg", mass, 1.0);
        map["g"] = make_unit("g", mass, 1e-3);
        map["mg"] = make_unit("mg", mass, 1e-6);
        map["ug"] = make_unit("ug", mass, 1e-9);
        map["t"] = make_unit("t", mass, 1e3);
        map["u"] = make_unit("u", mass, 1.66053906660e-27);

        map["m"] = make_unit("m", length, 1.0);
        map["km"] = make_unit("km", length, 1e3);
        map["cm"] = make_unit("cm", length, 1e-2);
        map["mm"] = make_unit("mm", length, 1e-3);
        map["um"] = make_unit("um", length, 1e-6);
        map["nm"] = make_unit("nm", length, 1e-9);
        map["pm"] = make_unit("pm", length, 1e-12);
        map["angstrom"] = make_unit("angstrom", length, 1e-10);
        map["Å"] = make_unit("Å", length, 1e-10);
        map["bohr"] = make_unit("bohr", length, 5.29177210903e-11);

        map["s"] = make_unit("s", time, 1.0);
        map["ms"] = make_unit("ms", time, 1e-3);
        map["us"] = make_unit("us", time, 1e-6);
        map["ns"] = make_unit("ns", time, 1e-9);
        map["min"] = make_unit("min", time, 60.0);
        map["h"] = make_unit("h", time, 3600.0);

        map["K"] = make_unit("K", temperature, 1.0);
        map["mK"] = make_unit("mK", temperature, 1e-3);

        map["A"] = make_unit("A", current, 1.0);
        map["mA"] = make_unit("mA", current, 1e-3);

        map["mol"] = make_unit("mol", amount, 1.0);
        map["mmol"] = make_unit("mmol", amount, 1e-3);

        map["cd"] = make_unit("cd", luminosity, 1.0);

        map["N"] = make_unit("N", make_dim(1, 1, -2, 0, 0, 0, 0), 1.0);
        map["kN"] = make_unit("kN", make_dim(1, 1, -2, 0, 0, 0, 0), 1e3);
        map["Pa"] = make_unit("Pa", make_dim(1, -1, -2, 0, 0, 0, 0), 1.0);
        map["hPa"] = make_unit("hPa", make_dim(1, -1, -2, 0, 0, 0, 0), 1e2);
        map["kPa"] = make_unit("kPa", make_dim(1, -1, -2, 0, 0, 0, 0), 1e3);
        map["MPa"] = make_unit("MPa", make_dim(1, -1, -2, 0, 0, 0, 0), 1e6);
        map["GPa"] = make_unit("GPa", make_dim(1, -1, -2, 0, 0, 0, 0), 1e9);
        map["bar"] = make_unit("bar", make_dim(1, -1, -2, 0, 0, 0, 0), 1e5);
        map["J"] = make_unit("J", make_dim(1, 2, -2, 0, 0, 0, 0), 1.0);
        map["kJ"] = make_unit("kJ", make_dim(1, 2, -2, 0, 0, 0, 0), 1e3);
        map["MJ"] = make_unit("MJ", make_dim(1, 2, -2, 0, 0, 0, 0), 1e6);
        map["eV"] = make_unit("eV", make_dim(1, 2, -2, 0, 0, 0, 0), 1.602176634e-19);
        map["W"] = make_unit("W", make_dim(1, 2, -3, 0, 0, 0, 0), 1.0);
        map["kW"] = make_unit("kW", make_dim(1, 2, -3, 0, 0, 0, 0), 1e3);
        map["MW"] = make_unit("MW", make_dim(1, 2, -3, 0, 0, 0, 0), 1e6);
        map["Hz"] = make_unit("Hz", make_dim(0, 0, -1, 0, 0, 0, 0), 1.0);
        map["C"] = make_unit("C", make_dim(0, 0, 1, 0, 1, 0, 0), 1.0);
        map["V"] = make_unit("V", make_dim(1, 2, -3, 0, -1, 0, 0), 1.0);
        map["ohm"] = make_unit("ohm", make_dim(1, 2, -3, 0, -2, 0, 0), 1.0);
        map["S"] = make_unit("S", make_dim(-1, -2, 3, 0, 2, 0, 0), 1.0);
        map["F"] = make_unit("F", make_dim(-1, -2, 4, 0, 2, 0, 0), 1.0);
        map["T"] = make_unit("T", make_dim(1, 0, -2, 0, -1, 0, 0), 1.0);
        map["Wb"] = make_unit("Wb", make_dim(1, 2, -2, 0, -1, 0, 0), 1.0);

        map["l"] = make_unit("l", make_dim(0, 3, 0, 0, 0, 0, 0), 1e-3);
        map["L"] = make_unit("L", make_dim(0, 3, 0, 0, 0, 0, 0), 1e-3);
        map["mL"] = make_unit("mL", make_dim(0, 3, 0, 0, 0, 0, 0), 1e-6);

        map["1"] = make_unit("1", dimensionless, 1.0);
        map["dimensionless"] = make_unit("dimensionless", dimensionless, 1.0);
        map["%"] = make_unit("%", dimensionless, 0.01);
        map["ppm"] = make_unit("ppm", dimensionless, 1e-6);
        map["PSU"] = make_unit("PSU", dimensionless, 1.0);
        map["rad"] = make_unit("rad", dimensionless, 1.0);
        map["deg"] = make_unit("deg", dimensionless, 3.14159265358979323846 / 180.0);
        map["rpm"] = make_unit("rpm", make_dim(0, 0, -1, 0, 0, 0, 0), 2.0 * 3.14159265358979323846 / 60.0);
        return map;
    }();
    return table;
}

const std::unordered_map<std::string, std::string>& aliases() {
    static const std::unordered_map<std::string, std::string> table = {
        {"µm", "um"}, {"μm", "um"}, {"Ohm", "ohm"}, {"Ω", "ohm"}, {"Å", "angstrom"},
    };
    return table;
}

bool is_name_char(unsigned char ch) {
    return std::isalpha(ch) || ch == '_' || ch == '%' || static_cast<bool>(ch & 0x80);
}

std::string trimmed(const std::string& text) {
    std::size_t begin = 0;
    std::size_t end = text.size();
    while (begin < end && std::isspace(static_cast<unsigned char>(text[begin]))) ++begin;
    while (end > begin && std::isspace(static_cast<unsigned char>(text[end - 1]))) --end;
    return text.substr(begin, end - begin);
}

std::vector<std::string> tokenize(const std::string& expression) {
    std::vector<std::string> tokens;
    std::size_t pos = 0;
    while (pos < expression.size()) {
        unsigned char ch = static_cast<unsigned char>(expression[pos]);
        if (std::isspace(ch)) {
            ++pos;
            continue;
        }
        if (ch == 0xC2 && pos + 1 < expression.size() && static_cast<unsigned char>(expression[pos + 1]) == 0xB7) {
            tokens.emplace_back("*");
            pos += 2;
            continue;
        }
        if (ch == 0xC3 && pos + 1 < expression.size() && static_cast<unsigned char>(expression[pos + 1]) == 0x97) {
            tokens.emplace_back("*");
            pos += 2;
            continue;
        }
        if (is_name_char(ch)) {
            std::size_t start = pos;
            while (pos < expression.size() && is_name_char(static_cast<unsigned char>(expression[pos]))) ++pos;
            tokens.push_back(expression.substr(start, pos - start));
            continue;
        }
        if (std::isdigit(ch) || ch == '.') {
            std::size_t start = pos;
            while (pos < expression.size() &&
                   (std::isdigit(static_cast<unsigned char>(expression[pos])) || expression[pos] == '.')) {
                ++pos;
            }
            tokens.push_back(expression.substr(start, pos - start));
            continue;
        }
        if (ch == '^' || ch == '*' || ch == '/' || ch == '(' || ch == ')' || ch == '+' || ch == '-') {
            tokens.emplace_back(1, static_cast<char>(ch));
            ++pos;
            continue;
        }
        throw UnitError(std::string("invalid character in unit expression: '") + expression[pos] + "'");
    }
    return tokens;
}

class UnitParser {
public:
    UnitParser(std::vector<std::string> tokens, std::string expression)
        : tokens_(std::move(tokens)), expression_(std::move(expression)) {}

    Unit parse() {
        Unit unit = expr();
        if (index_ != tokens_.size()) throw UnitError("trailing tokens in unit expression: " + expression_);
        return unit;
    }

private:
    const std::string* peek() const { return index_ < tokens_.size() ? &tokens_[index_] : nullptr; }

    std::string next() {
        const std::string* token = peek();
        if (token == nullptr) throw UnitError("unexpected end of unit expression: " + expression_);
        return tokens_[index_++];
    }

    Unit expr() {
        Unit unit = factor();
        while (peek() != nullptr && (*peek() == "*" || *peek() == "/")) {
            std::string op = next();
            Unit rhs = factor();
            unit = (op == "*") ? unit * rhs : unit / rhs;
        }
        return unit;
    }

    Unit factor() {
        std::string token = next();
        Unit unit;
        if (token == "(") {
            unit = expr();
            if (next() != ")") throw UnitError("missing ')' in unit expression: " + expression_);
        } else if (token == "+" || token == "-") {
            unit = factor();
        } else if (is_number_token(token)) {
            unit.symbol = token;
            unit.scale = std::strtod(token.c_str(), nullptr);
        } else {
            unit = get_unit(token);
        }
        if (peek() != nullptr && *peek() == "^") {
            next();
            int sign = 1;
            if (peek() != nullptr && *peek() == "-") {
                next();
                sign = -1;
            }
            std::string exponent = next();
            if (!is_number_token(exponent) || exponent.find('.') != std::string::npos) {
                throw UnitError("unit exponents must be integers: " + exponent);
            }
            unit = unit.pow(sign * std::atoi(exponent.c_str()));
        }
        return unit;
    }

    std::vector<std::string> tokens_;
    std::string expression_;
    std::size_t index_ = 0;
};

}  // namespace

std::string format_general(double value) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%g", value);
    return std::string(buffer);
}

Dimension Dimension::base(int index) {
    Dimension dimension;
    dimension.exponents[static_cast<std::size_t>(index)] = 1;
    return dimension;
}

bool Dimension::dimensionless() const {
    for (int exponent : exponents) {
        if (exponent != 0) return false;
    }
    return true;
}

Dimension Dimension::operator*(const Dimension& other) const {
    Dimension result;
    for (std::size_t i = 0; i < exponents.size(); ++i) result.exponents[i] = exponents[i] + other.exponents[i];
    return result;
}

Dimension Dimension::operator/(const Dimension& other) const {
    Dimension result;
    for (std::size_t i = 0; i < exponents.size(); ++i) result.exponents[i] = exponents[i] - other.exponents[i];
    return result;
}

Dimension Dimension::pow(int power) const {
    Dimension result;
    for (std::size_t i = 0; i < exponents.size(); ++i) result.exponents[i] = exponents[i] * power;
    return result;
}

std::string Dimension::to_string() const {
    std::string text;
    for (std::size_t i = 0; i < exponents.size(); ++i) {
        if (exponents[i] == 0) continue;
        if (!text.empty()) text += " * ";
        text += kBaseNames[i];
        if (exponents[i] != 1) text += "^" + std::to_string(exponents[i]);
    }
    return text.empty() ? "dimensionless" : text;
}

bool Unit::is_dimensionless() const {
    return dimension.dimensionless() && std::fabs(scale - 1.0) < 1e-12;
}

Unit Unit::operator*(const Unit& other) const {
    return Unit{symbol + "*" + other.symbol, dimension * other.dimension, scale * other.scale};
}

Unit Unit::operator/(const Unit& other) const {
    return Unit{symbol + "/" + other.symbol, dimension / other.dimension, scale / other.scale};
}

Unit Unit::pow(int power) const {
    return Unit{symbol + "^" + std::to_string(power), dimension.pow(power), std::pow(scale, power)};
}

bool Unit::operator==(const Unit& other) const {
    return dimension == other.dimension && std::fabs(scale - other.scale) < 1e-12;
}

double Quantity::as(const Unit& target) const {
    if (target.dimension != unit.dimension) {
        throw UnitError("cannot convert '" + unit.symbol + "' to '" + target.symbol + "': incompatible dimensions");
    }
    return si_value() / target.scale;
}

std::string Quantity::to_string() const {
    if (unit.symbol.empty() || unit.symbol == "1" || unit.symbol == "dimensionless") return format_general(value);
    return format_general(value) + " " + unit.symbol;
}

const Unit& dimensionless_unit() {
    static const Unit unit = make_unit("", Dimension{}, 1.0);
    return unit;
}

const Unit& get_unit(const std::string& name) {
    auto alias = aliases().find(name);
    const std::string& resolved = alias != aliases().end() ? alias->second : name;
    auto it = registry().find(resolved);
    if (it != registry().end()) return it->second;
    throw UnitError("unknown unit: '" + name + "'");
}

void register_unit(const std::string& name, const Unit& unit) {
    const_cast<std::unordered_map<std::string, Unit>&>(registry())[name] = unit;
}

Unit parse_unit(const std::string& expression) {
    std::string text = trimmed(expression);
    if (text.empty()) throw UnitError("empty unit expression");
    return UnitParser(tokenize(text), text).parse();
}

bool is_number_token(const std::string& text) {
    if (text.empty()) return false;
    std::size_t i = 0;
    if (text[i] == '+' || text[i] == '-') ++i;
    bool digits = false;
    while (i < text.size() && std::isdigit(static_cast<unsigned char>(text[i]))) {
        ++i;
        digits = true;
    }
    if (i < text.size() && text[i] == '.') {
        ++i;
        while (i < text.size() && std::isdigit(static_cast<unsigned char>(text[i]))) {
            ++i;
            digits = true;
        }
    }
    if (!digits) return false;
    if (i < text.size() && (text[i] == 'e' || text[i] == 'E')) {
        ++i;
        if (i < text.size() && (text[i] == '+' || text[i] == '-')) ++i;
        bool exp_digits = false;
        while (i < text.size() && std::isdigit(static_cast<unsigned char>(text[i]))) {
            ++i;
            exp_digits = true;
        }
        if (!exp_digits) return false;
    }
    return i == text.size();
}

Quantity parse_quantity(const std::string& input) {
    std::string text = trimmed(input);
    if (text.empty()) throw UnitError("empty quantity");
    if (is_number_token(text)) return Quantity{std::strtod(text.c_str(), nullptr), dimensionless_unit()};
    if (text.size() >= 2 && text.back() == '%' && is_number_token(trimmed(text.substr(0, text.size() - 1)))) {
        std::string number = trimmed(text.substr(0, text.size() - 1));
        return Quantity{std::strtod(number.c_str(), nullptr), get_unit("%")};
    }
    std::size_t split = std::string::npos;
    for (std::size_t i = 0; i < text.size(); ++i) {
        if (std::isspace(static_cast<unsigned char>(text[i]))) {
            split = i;
            break;
        }
    }
    if (split != std::string::npos) {
        std::string number = trimmed(text.substr(0, split));
        std::string unit = trimmed(text.substr(split));
        if (is_number_token(number) && !unit.empty()) {
            return Quantity{std::strtod(number.c_str(), nullptr), parse_unit(unit)};
        }
    }
    throw UnitError("cannot parse quantity: '" + text + "'");
}

std::optional<Quantity> try_quantity(const std::string& text) {
    std::string low;
    low.reserve(text.size());
    for (char ch : text) low.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
    std::string trimmed_low = trimmed(low);
    if (trimmed_low == "parameterized" || trimmed_low == "true" || trimmed_low == "false") return std::nullopt;
    try {
        return parse_quantity(text);
    } catch (const UnitError&) {
        return std::nullopt;
    }
}

}  // namespace ums
