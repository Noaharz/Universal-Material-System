#pragma once

#include <stdexcept>
#include <string>

namespace ums {

class UmsError : public std::runtime_error {
public:
    explicit UmsError(const std::string& message) : std::runtime_error(message) {}
};

class ParseError : public UmsError {
public:
    ParseError(const std::string& message, int line, int column, std::string path = std::string())
        : UmsError(build(message, line, column, path)), line_(line), column_(column), path_(std::move(path)) {}

    int line() const { return line_; }
    int column() const { return column_; }
    const std::string& path() const { return path_; }

private:
    static std::string build(const std::string& message, int line, int column, const std::string& path) {
        std::string text = message;
        if (line > 0) {
            text += " at line " + std::to_string(line) + " column " + std::to_string(column);
        }
        if (!path.empty()) text += " (" + path + ")";
        return text;
    }

    int line_ = 0;
    int column_ = 0;
    std::string path_;
};

class UnitError : public UmsError {
public:
    explicit UnitError(const std::string& message) : UmsError(message) {}
};

class ValidationError : public UmsError {
public:
    explicit ValidationError(const std::string& message) : UmsError(message) {}
};

class ResourceNotFound : public UmsError {
public:
    explicit ResourceNotFound(const std::string& message) : UmsError(message) {}
};

class CyclicDependencyError : public UmsError {
public:
    explicit CyclicDependencyError(const std::string& message) : UmsError(message) {}
};

}  // namespace ums
