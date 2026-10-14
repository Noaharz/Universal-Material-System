#pragma once

#include <string>

#include "ums/parser.hpp"
#include "ums/value.hpp"

namespace ums {

std::string serialize_document(DocumentType type, const Value& sections);
std::string format_scalar(const Value& value);

}  // namespace ums
