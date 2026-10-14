#pragma once

#include <string>

#include "ums/parser.hpp"

namespace ums {

std::string read_file(const std::string& path);
Document parse_file(const std::string& path);

}  // namespace ums
