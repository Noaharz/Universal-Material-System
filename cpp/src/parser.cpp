#include "ums/parser.hpp"

#include <cctype>
#include <cstdlib>
#include <vector>

#include "ums/errors.hpp"

namespace ums {

namespace {

struct Line {
    int indent;
    std::string text;
    int number;
};

std::string trim(std::string_view text) {
    std::size_t begin = 0;
    std::size_t end = text.size();
    while (begin < end && std::isspace(static_cast<unsigned char>(text[begin]))) ++begin;
    while (end > begin && std::isspace(static_cast<unsigned char>(text[end - 1]))) --end;
    return std::string(text.substr(begin, end - begin));
}

bool starts_with_dash(const std::string& text) {
    return text.size() >= 2 && text[0] == '-' && text[1] == ' ';
}

bool is_int_token(const std::string& text) {
    if (text.empty()) return false;
    std::size_t i = 0;
    if (text[i] == '+' || text[i] == '-') ++i;
    if (i >= text.size()) return false;
    for (; i < text.size(); ++i) {
        if (!std::isdigit(static_cast<unsigned char>(text[i]))) return false;
    }
    return true;
}

bool looks_numeric(const std::string& text) {
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

std::vector<Line> prepare(std::string_view text) {
    std::vector<Line> lines;
    std::size_t pos = 0;
    int number = 0;
    while (pos <= text.size()) {
        std::size_t newline = text.find('\n', pos);
        std::string_view raw = newline == std::string_view::npos ? text.substr(pos) : text.substr(pos, newline - pos);
        pos = newline == std::string_view::npos ? text.size() + 1 : newline + 1;
        ++number;
        if (!raw.empty() && raw.back() == '\r') raw.remove_suffix(1);

        std::string stripped = trim(raw);
        if (stripped.empty() || stripped[0] == '#') continue;

        std::string expanded;
        expanded.reserve(raw.size());
        for (char ch : raw) {
            if (ch == '\t') {
                expanded += "    ";
            } else {
                expanded.push_back(ch);
            }
        }
        std::size_t indent = 0;
        while (indent < expanded.size() && expanded[indent] == ' ') ++indent;
        lines.push_back(Line{static_cast<int>(indent), trim(expanded), number});
    }
    return lines;
}

bool split_key(const std::string& text, std::string& key, std::string& rest) {
    char quote = 0;
    for (std::size_t i = 0; i < text.size(); ++i) {
        char ch = text[i];
        if (quote) {
            if (ch == quote) quote = 0;
            continue;
        }
        if (ch == '\'' || ch == '"') {
            quote = ch;
        } else if (ch == ':') {
            key = trim(text.substr(0, i));
            rest = trim(text.substr(i + 1));
            return true;
        }
    }
    return false;
}

std::vector<Value> parse_flow_list(const std::string& text) {
    std::string inner = trim(std::string_view(text).substr(1, text.size() - 2));
    std::vector<Value> items;
    if (inner.empty()) return items;

    int depth = 0;
    char quote = 0;
    std::string current;
    for (char ch : inner) {
        if (quote) {
            current.push_back(ch);
            if (ch == quote) quote = 0;
            continue;
        }
        if (ch == '\'' || ch == '"') {
            quote = ch;
            current.push_back(ch);
        } else if (ch == '[' || ch == '{') {
            depth++;
            current.push_back(ch);
        } else if (ch == ']' || ch == '}') {
            depth--;
            current.push_back(ch);
        } else if (ch == ',' && depth == 0) {
            items.push_back(parse_scalar(current));
            current.clear();
        } else {
            current.push_back(ch);
        }
    }
    if (!trim(current).empty()) items.push_back(parse_scalar(current));
    return items;
}

class BlockParser {
public:
    BlockParser(const std::vector<Line>& lines, std::string path)
        : lines_(lines), path_(std::move(path)) {}

    Value parse() {
        const Line* line = current();
        if (line == nullptr) return Value::map();
        return block(line->indent);
    }

private:
    const Line* current() const { return index_ < lines_.size() ? &lines_[index_] : nullptr; }

    [[noreturn]] void fail(const std::string& message, const Line& line) const {
        throw ParseError(message, line.number, line.indent + 1, path_);
    }

    Value block(int indent) {
        const Line* line = current();
        if (line == nullptr) return Value::map();
        if (starts_with_dash(line->text)) return parse_list(indent);
        return parse_mapping(indent);
    }

    Value parse_list(int indent) {
        std::vector<Value> items;
        while (true) {
            const Line* line = current();
            if (line == nullptr || line->indent < indent || !starts_with_dash(line->text)) break;
            if (line->indent > indent) fail("unexpected indentation in list", *line);
            std::string content = trim(std::string_view(line->text).substr(2));
            index_++;
            if (content.empty()) {
                const Line* nxt = current();
                if (nxt != nullptr && nxt->indent > indent) {
                    items.push_back(block(nxt->indent));
                } else {
                    items.push_back(Value::null());
                }
                continue;
            }
            std::string key;
            std::string rest;
            if (split_key(content, key, rest)) {
                Value item = Value::map();
                if (rest.empty()) {
                    const Line* nxt = current();
                    if (nxt != nullptr && nxt->indent > indent) {
                        item.set_field(key, block(nxt->indent));
                    } else {
                        item.set_field(key, Value::null());
                    }
                } else {
                    item.set_field(key, parse_inline_value(rest));
                }
                const Line* nxt = current();
                if (nxt != nullptr && nxt->indent > indent) {
                    Value extra = parse_mapping(nxt->indent);
                    for (const auto& entry : extra.fields()) item.set_field(entry.first, entry.second);
                }
                items.push_back(std::move(item));
            } else {
                items.push_back(parse_inline_value(content));
                const Line* nxt = current();
                if (nxt != nullptr && nxt->indent > indent) fail("scalar list items cannot have children", *nxt);
            }
        }
        return Value::list(std::move(items));
    }

    Value parse_mapping(int indent) {
        Value result = Value::map();
        while (true) {
            const Line* line = current();
            if (line == nullptr || line->indent < indent) break;
            if (line->indent > indent) fail("unexpected indentation", *line);
            if (starts_with_dash(line->text)) break;
            std::string key;
            std::string rest;
            if (!split_key(line->text, key, rest)) {
                fail("expected 'Key: value', got '" + line->text + "'", *line);
            }
            if (key.empty()) fail("empty key", *line);
            index_++;
            if (rest.empty()) {
                const Line* nxt = current();
                if (nxt != nullptr && nxt->indent > indent) {
                    result.set_field(key, block(nxt->indent));
                } else {
                    result.set_field(key, Value::null());
                }
            } else {
                result.set_field(key, parse_inline_value(rest));
            }
        }
        return result;
    }

    const std::vector<Line>& lines_;
    std::string path_;
    std::size_t index_ = 0;
};

}  // namespace

DocumentType document_type_from_token(const std::string& token) {
    std::string normalized;
    for (char ch : token) {
        if (!std::isspace(static_cast<unsigned char>(ch))) {
            normalized.push_back(static_cast<char>(std::toupper(static_cast<unsigned char>(ch))));
        }
    }
    if (normalized == "ATOM") return DocumentType::Atom;
    if (normalized == "STRUCTURE" || normalized == "MOLECULE") return DocumentType::Structure;
    if (normalized == "MATERIAL") return DocumentType::Material;
    if (normalized == "INSTANCE" || normalized == "MATERIALINSTANCE") return DocumentType::Instance;
    throw ParseError("unknown document type keyword: '" + token + "'", 0, 0);
}

std::string to_string(DocumentType type) {
    switch (type) {
        case DocumentType::Atom:
            return "atom";
        case DocumentType::Structure:
            return "structure";
        case DocumentType::Material:
            return "material";
        case DocumentType::Instance:
            return "instance";
    }
    return "unknown";
}

std::string keyword(DocumentType type) {
    switch (type) {
        case DocumentType::Atom:
            return "ATOM";
        case DocumentType::Structure:
            return "STRUCTURE";
        case DocumentType::Material:
            return "MATERIAL";
        case DocumentType::Instance:
            return "INSTANCE";
    }
    return "ATOM";
}

bool is_document_suffix(const std::string& suffix) {
    return suffix == ".atom" || suffix == ".structure" || suffix == ".material" || suffix == ".instance";
}

Value parse_scalar(std::string_view input) {
    std::string text = trim(input);
    if (text.size() >= 2 && text.front() == text.back() && (text.front() == '\'' || text.front() == '"')) {
        return Value::str(text.substr(1, text.size() - 2));
    }

    std::string lowered;
    lowered.reserve(text.size());
    for (char ch : text) lowered.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));

    if (lowered == "true") return Value::boolean(true);
    if (lowered == "false") return Value::boolean(false);
    if (lowered == "null" || lowered == "none" || lowered == "~") return Value::null();

    if (is_int_token(text)) return Value::integer(std::strtoll(text.c_str(), nullptr, 10));
    if (looks_numeric(text)) return Value::number(std::strtod(text.c_str(), nullptr));
    return Value::str(text);
}

Value parse_inline_value(std::string_view text) {
    std::string stripped = trim(text);
    if (stripped.size() >= 2 && stripped.front() == '[' && stripped.back() == ']') {
        return Value::list(parse_flow_list(stripped));
    }
    return parse_scalar(stripped);
}

Document parse_document(std::string_view text, const std::string& path) {
    std::vector<Line> lines = prepare(text);
    if (lines.empty()) throw ParseError("empty document", 1, 1, path);
    const Line& first = lines.front();
    if (first.indent != 0) throw ParseError("document type keyword must not be indented", first.number, 1, path);

    Document document;
    try {
        document.type = document_type_from_token(first.text);
    } catch (const ParseError&) {
        throw ParseError("unknown document type keyword: '" + first.text + "'", first.number, 1, path);
    }
    document.path = path;

    if (lines.size() == 1) {
        document.sections = Value::map();
        return document;
    }
    std::vector<Line> body(lines.begin() + 1, lines.end());
    Value sections = BlockParser(body, path).parse();
    if (!sections.is_map()) throw ParseError("document body must be a mapping of sections", 1, 1, path);
    document.sections = std::move(sections);
    return document;
}

Document parse_buffer(const char* data, std::size_t size, const std::string& path) {
    return parse_document(std::string_view(data, size), path);
}

}  // namespace ums
