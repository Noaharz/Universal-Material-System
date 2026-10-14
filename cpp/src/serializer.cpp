#include "ums/serializer.hpp"

#include <cctype>
#include <cstdlib>
#include <vector>

#include "ums/units.hpp"

namespace ums {

namespace {

const std::string kSpecialChars = ".,/:{}[]#&*!|>'\"%@`\t ";

bool python_float_parseable(const std::string& text) {
    if (text.empty()) return false;
    const char* begin = text.c_str();
    char* end = nullptr;
    std::strtod(begin, &end);
    return end == begin + text.size();
}

bool needs_quote(const std::string& text) {
    if (text.empty()) return true;
    if (text[0] == '-' || text[0] == '?') return true;
    if (try_quantity(text).has_value()) return false;
    for (char ch : text) {
        if (kSpecialChars.find(ch) != std::string::npos) return true;
    }
    std::string lowered;
    lowered.reserve(text.size());
    for (char ch : text) lowered.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
    if (lowered == "true" || lowered == "false" || lowered == "null" || lowered == "none" || lowered == "~") return true;
    if (python_float_parseable(text)) return true;
    return false;
}

std::string quote_string(const std::string& text) {
    std::string result = "\"";
    for (char ch : text) {
        if (ch == '"') {
            result += "\\\"";
        } else {
            result.push_back(ch);
        }
    }
    result.push_back('"');
    return result;
}

void emit_value(const Value& value, int indent, std::vector<std::string>& out);

void emit_mapping(const Value& mapping, int indent, std::vector<std::string>& out) {
    std::string pad(static_cast<std::size_t>(indent), ' ');
    for (const auto& entry : mapping.fields()) {
        const Value& child = entry.second;
        bool container = child.is_map() || child.is_list();
        if (container && !(child.is_map() ? child.fields().empty() : child.items().empty())) {
            out.push_back(pad + entry.first + ":");
            emit_value(child, indent + 4, out);
        } else if (container) {
            out.push_back(pad + entry.first + ":");
            emit_value(child, indent + 4, out);
        } else {
            out.push_back(pad + entry.first + ": " + format_scalar(child));
        }
    }
}

void emit_sequence(const Value& sequence, int indent, std::vector<std::string>& out) {
    std::string pad(static_cast<std::size_t>(indent), ' ');
    for (const auto& item : sequence.items()) {
        if (item.is_map() && !item.fields().empty()) {
            const auto& fields = item.fields();
            const std::string& first_key = fields.front().first;
            const Value& first_value = fields.front().second;
            bool container = first_value.is_map() || first_value.is_list();
            bool non_empty = first_value.is_map() ? !first_value.fields().empty() : !first_value.items().empty();
            if (container && non_empty) {
                out.push_back(pad + "- " + first_key + ":");
                emit_value(first_value, indent + 4, out);
            } else {
                out.push_back(pad + "- " + first_key + ": " + format_scalar(first_value));
            }
            if (fields.size() > 1) {
                Value rest = Value::map();
                for (std::size_t i = 1; i < fields.size(); ++i) rest.set_field(fields[i].first, fields[i].second);
                emit_mapping(rest, indent + 2, out);
            }
        } else if (item.is_map()) {
            out.push_back(pad + "-");
        } else if (item.is_list()) {
            out.push_back(pad + "-");
            emit_value(item, indent + 2, out);
        } else {
            out.push_back(pad + "- " + format_scalar(item));
        }
    }
}

void emit_value(const Value& value, int indent, std::vector<std::string>& out) {
    if (value.is_map()) {
        emit_mapping(value, indent, out);
    } else if (value.is_list()) {
        emit_sequence(value, indent, out);
    }
}

}  // namespace

std::string format_scalar(const Value& value) {
    switch (value.type) {
        case Value::Type::Null:
            return "null";
        case Value::Type::Bool:
            return value.bool_value ? "true" : "false";
        case Value::Type::Int:
            return std::to_string(value.int_value);
        case Value::Type::Float:
            return format_general(value.float_value);
        case Value::Type::String: {
            const std::string& text = value.string_value;
            if (needs_quote(text)) return quote_string(text);
            return text;
        }
        case Value::Type::List:
            return "[]";
        case Value::Type::Map:
            return "{}";
    }
    return std::string();
}

std::string serialize_document(DocumentType type, const Value& sections) {
    std::vector<std::string> lines;
    lines.push_back(keyword(type));
    lines.push_back("");
    emit_mapping(sections, 0, lines);
    std::string result;
    for (std::size_t i = 0; i < lines.size(); ++i) {
        if (i != 0) result += "\n";
        result += lines[i];
    }
    result += "\n";
    return result;
}

}  // namespace ums
