#pragma once

#include <ostream>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace ums {

struct Value {
    enum class Type { Null, Bool, Int, Float, String, List, Map };

    Type type = Type::Null;
    bool bool_value = false;
    long long int_value = 0;
    double float_value = 0.0;
    std::string string_value;
    std::vector<Value> list_value;
    std::vector<std::pair<std::string, Value>> map_value;

    static Value null() { return Value{}; }

    static Value boolean(bool b) {
        Value v;
        v.type = Type::Bool;
        v.bool_value = b;
        return v;
    }

    static Value integer(long long i) {
        Value v;
        v.type = Type::Int;
        v.int_value = i;
        return v;
    }

    static Value number(double d) {
        Value v;
        v.type = Type::Float;
        v.float_value = d;
        return v;
    }

    static Value str(std::string s) {
        Value v;
        v.type = Type::String;
        v.string_value = std::move(s);
        return v;
    }

    static Value list(std::vector<Value> items) {
        Value v;
        v.type = Type::List;
        v.list_value = std::move(items);
        return v;
    }

    static Value map() {
        Value v;
        v.type = Type::Map;
        return v;
    }

    bool is_null() const { return type == Type::Null; }
    bool is_bool() const { return type == Type::Bool; }
    bool is_int() const { return type == Type::Int; }
    bool is_float() const { return type == Type::Float; }
    bool is_number() const { return type == Type::Int || type == Type::Float; }
    bool is_string() const { return type == Type::String; }
    bool is_list() const { return type == Type::List; }
    bool is_map() const { return type == Type::Map; }

    bool as_bool(bool fallback = false) const { return type == Type::Bool ? bool_value : fallback; }

    long long as_int(long long fallback = 0) const {
        if (type == Type::Int) return int_value;
        if (type == Type::Float) return static_cast<long long>(float_value);
        return fallback;
    }

    double as_double(double fallback = 0.0) const {
        if (type == Type::Float) return float_value;
        if (type == Type::Int) return static_cast<double>(int_value);
        return fallback;
    }

    std::string as_string(const std::string& fallback = std::string()) const {
        return type == Type::String ? string_value : fallback;
    }

    const std::vector<Value>& items() const { return list_value; }
    const std::vector<std::pair<std::string, Value>>& fields() const { return map_value; }

    const Value* field(const std::string& key) const {
        for (const auto& entry : map_value) {
            if (entry.first == key) return &entry.second;
        }
        return nullptr;
    }

    void set_field(const std::string& key, Value value) {
        for (auto& entry : map_value) {
            if (entry.first == key) {
                entry.second = std::move(value);
                return;
            }
        }
        map_value.emplace_back(key, std::move(value));
    }

    std::string scalar_text() const {
        switch (type) {
            case Type::Null:
                return "null";
            case Type::Bool:
                return bool_value ? "true" : "false";
            case Type::Int:
                return std::to_string(int_value);
            case Type::Float: {
                std::ostringstream out;
                out << float_value;
                return out.str();
            }
            case Type::String:
                return string_value;
            default:
                return is_list() ? "[list]" : "{map}";
        }
    }

    void dump(std::ostream& out, int indent = 0) const {
        std::string pad(static_cast<std::size_t>(indent) * 4, ' ');
        switch (type) {
            case Type::List:
                if (list_value.empty()) {
                    out << pad << "[]\n";
                    break;
                }
                for (const auto& item : list_value) {
                    if (item.is_map()) {
                        out << pad << "-\n";
                        item.dump(out, indent + 1);
                    } else if (item.is_list()) {
                        out << pad << "-\n";
                        item.dump(out, indent + 1);
                    } else {
                        out << pad << "- " << item.scalar_text() << "\n";
                    }
                }
                break;
            case Type::Map:
                if (map_value.empty()) {
                    out << pad << "{}\n";
                    break;
                }
                for (const auto& entry : map_value) {
                    const Value& child = entry.second;
                    if (child.is_map() || child.is_list()) {
                        out << pad << entry.first << ":\n";
                        child.dump(out, indent + 1);
                    } else {
                        out << pad << entry.first << ": " << child.scalar_text() << "\n";
                    }
                }
                break;
            default:
                out << pad << scalar_text() << "\n";
                break;
        }
    }
};

}  // namespace ums
