#pragma once

#include <string>

#include "ums/parser.hpp"
#include "ums/reader.hpp"
#include "ums/value.hpp"

namespace ums {

// A small builder for UMS documents. An importer can assemble sections as
// typed values and then serialize them canonically, so that what it writes
// round-trips through the parser unchanged.
class DocumentWriter {
public:
    explicit DocumentWriter(DocumentType type);

    DocumentType type() const { return type_; }
    Value& sections() { return sections_; }
    const Value& sections() const { return sections_; }

    void set_identity(const Identity& identity);
    void set_identity(const std::string& id, const std::string& name,
                      const std::string& category = std::string(), int version = 1);

    Value& section(const std::string& key);
    void set_section(const std::string& key, Value value);
    void set_field(const std::string& section_key, const std::string& key, Value value);
    void append(const std::string& section_key, Value value);

    void set_appearance(Value appearance) { set_section("Appearance", std::move(appearance)); }
    void set_contact(Value contact) { set_section("Contact", std::move(contact)); }

    std::string text() const;
    Document document(const std::string& path = std::string()) const;

private:
    DocumentType type_;
    Value sections_;
};

}  // namespace ums
