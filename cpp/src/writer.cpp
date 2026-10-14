#include "ums/writer.hpp"

#include <utility>

#include "ums/serializer.hpp"

namespace ums {

DocumentWriter::DocumentWriter(DocumentType type) : type_(type) { sections_ = Value::map(); }

void DocumentWriter::set_identity(const Identity& identity) {
    sections_.set_field("Version", Value::integer(identity.version));
    Value identity_section = Value::map();
    identity_section.set_field("Id", Value::str(identity.id));
    identity_section.set_field("Name", Value::str(identity.name));
    if (!identity.category.empty()) identity_section.set_field("Category", Value::str(identity.category));
    sections_.set_field("Identity", std::move(identity_section));
}

void DocumentWriter::set_identity(const std::string& id, const std::string& name, const std::string& category,
                                  int version) {
    Identity identity;
    identity.id = id;
    identity.name = name;
    identity.category = category;
    identity.version = version;
    set_identity(identity);
}

Value& DocumentWriter::section(const std::string& key) {
    for (auto& entry : sections_.map_value) {
        if (entry.first == key) {
            if (!entry.second.is_map()) entry.second = Value::map();
            return entry.second;
        }
    }
    sections_.map_value.emplace_back(key, Value::map());
    return sections_.map_value.back().second;
}

void DocumentWriter::set_section(const std::string& key, Value value) { sections_.set_field(key, std::move(value)); }

void DocumentWriter::set_field(const std::string& section_key, const std::string& key, Value value) {
    section(section_key).set_field(key, std::move(value));
}

void DocumentWriter::append(const std::string& section_key, Value value) {
    Value& target = section(section_key);
    if (!target.is_list()) target = Value::list({});
    target.list_value.push_back(std::move(value));
}

std::string DocumentWriter::text() const { return serialize_document(type_, sections_); }

Document DocumentWriter::document(const std::string& path) const {
    Document document;
    document.type = type_;
    document.sections = sections_;
    document.path = path;
    return document;
}

}  // namespace ums
