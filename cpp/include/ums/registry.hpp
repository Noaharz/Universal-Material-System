#pragma once

#include <functional>
#include <map>
#include <string>
#include <unordered_map>
#include <vector>

#include "ums/parser.hpp"

namespace ums {

class ResourceRegistry {
public:
    using Resolver = std::function<std::string(const std::string&)>;

    void set_resolver(Resolver resolver) { resolver_ = std::move(resolver); }

    void add(const std::string& key, const std::string& logical_path, Document document);

    bool has(const std::string& ref) const;
    const Document* get(const std::string& ref) const;
    std::string canonical_key(const std::string& ref) const;

    std::string resource_id(const Document& document) const;
    std::vector<std::string> dependency_refs(const Document& document) const;

    std::vector<std::string> keys() const;
    std::vector<std::string> logical_paths() const;
    std::vector<std::string> sorted_ids() const;
    std::size_t size() const;

    bool has_key(const std::string& key) const;
    std::string key_for_path(const std::string& logical_path) const;

    std::map<std::string, std::vector<std::string>> dependencies(const std::string& ref, bool recursive = true) const;
    std::map<std::string, std::vector<std::string>> missing_references() const;
    void check_cycles() const;
    std::vector<std::string> dependents(const std::string& ref) const;

private:
    void walk(const std::string& key, std::map<std::string, std::vector<std::string>>& graph,
              std::vector<std::string>& visiting, bool recursive) const;

    std::unordered_map<std::string, Document> cache_;
    std::unordered_map<std::string, std::string> by_id_;
    std::unordered_map<std::string, std::string> by_path_;
    Resolver resolver_;
};

}  // namespace ums
