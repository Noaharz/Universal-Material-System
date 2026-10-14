#pragma once

#include <string>
#include <vector>

#include "ums/parser.hpp"
#include "ums/registry.hpp"

namespace ums {

class ResourceLibrary {
public:
    ResourceLibrary() = default;
    explicit ResourceLibrary(std::vector<std::string> search_paths);

    void add_search_path(const std::string& path);
    void index(bool force = false);

    bool has(const std::string& ref);
    const Document* load(const std::string& ref);

    std::vector<std::string> logical_paths() const;
    std::vector<std::string> sorted_ids() const;
    std::size_t size() const;

    const std::vector<std::string>& search_paths() const { return paths_; }
    std::string resource_id(const Document& document) const;
    std::vector<std::string> dependency_refs(const Document& document) const;

    ResourceRegistry& registry() { return registry_; }
    const ResourceRegistry& registry() const { return registry_; }

private:
    std::string resolve_path(const std::string& ref);
    std::string load_file(const std::string& file_path);

    std::vector<std::string> paths_;
    ResourceRegistry registry_;
    bool indexed_ = false;
};

}  // namespace ums
