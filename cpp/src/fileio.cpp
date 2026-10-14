#include "ums/fileio.hpp"

#ifndef UMS_NO_FILESYSTEM

#include <fstream>
#include <sstream>

#include "ums/errors.hpp"

namespace ums {

std::string read_file(const std::string& path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw UmsError("cannot open file: " + path);
    std::ostringstream buffer;
    buffer << stream.rdbuf();
    return buffer.str();
}

Document parse_file(const std::string& path) {
    return parse_document(read_file(path), path);
}

}  // namespace ums

#endif  // UMS_NO_FILESYSTEM
