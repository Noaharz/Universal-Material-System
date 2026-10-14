#pragma once

#include <cstddef>
#include <string>
#include <string_view>

#include "ums/result.hpp"
#include "ums/value.hpp"

namespace ums {

enum class DocumentType { Atom, Structure, Material, Instance };

DocumentType document_type_from_token(const std::string& token);
std::string to_string(DocumentType type);
std::string keyword(DocumentType type);
bool is_document_suffix(const std::string& suffix);

struct Document {
    DocumentType type = DocumentType::Atom;
    Value sections;
    std::string path;
};

Value parse_scalar(std::string_view text);
Value parse_inline_value(std::string_view text);
Document parse_document(std::string_view text, const std::string& path = std::string());
Document parse_buffer(const char* data, std::size_t size, const std::string& path = std::string());

using DocumentResult = Result<Document>;

// Non-throwing variants that report problems as a Diagnostic instead of
// throwing. Useful for host bindings and batched importers.
DocumentResult try_parse_document(std::string_view text, const std::string& path = std::string());
DocumentResult try_parse_buffer(const char* data, std::size_t size, const std::string& path = std::string());

}  // namespace ums
