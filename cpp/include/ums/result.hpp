#pragma once

#include <optional>
#include <string>
#include <utility>

namespace ums {

// A structured, non-throwing error description. It complements the exception
// based API so that hosts (for example WebAssembly bindings) can handle parse,
// unit and validation problems without exceptions.
struct Diagnostic {
    std::string code;
    std::string message;
    int line = 0;
    int column = 0;
    std::string path;
};

// A small std::expected-style result type. C++20 has no std::expected; this is
// an intentionally minimal, dependency-free stand-in with the same call shape.
template <typename T>
class Result {
public:
    static Result ok(T value) { return Result(std::move(value)); }
    static Result fail(Diagnostic diagnostic) { return Result(std::move(diagnostic)); }

    bool has_value() const { return value_.has_value(); }
    explicit operator bool() const { return has_value(); }

    T& value() { return value_.value(); }
    const T& value() const { return value_.value(); }
    T& operator*() { return value_.value(); }
    const T& operator*() const { return value_.value(); }
    T* operator->() { return &value_.value(); }
    const T* operator->() const { return &value_.value(); }

    const Diagnostic& error() const { return error_; }

private:
    explicit Result(T value) : value_(std::move(value)) {}
    explicit Result(Diagnostic diagnostic) : error_(std::move(diagnostic)) {}

    std::optional<T> value_;
    Diagnostic error_;
};

}  // namespace ums
