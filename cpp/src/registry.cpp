#include "ums/registry.hpp"

#include <algorithm>
#include <set>

#include "ums/errors.hpp"
#include "ums/reader.hpp"

namespace ums {

void ResourceRegistry::add(const std::string& key, const std::string& logical_path, Document document) {
    document.path = key;
    std::string id = resource_id(document);
    cache_[key] = std::move(document);
    if (!id.empty()) by_id_[id] = key;
    if (!logical_path.empty()) by_path_[logical_path] = key;
}

std::string ResourceRegistry::resource_id(const Document& document) const {
    switch (document.type) {
        case DocumentType::Atom:
            return read_atom(document).identity.id;
        case DocumentType::Structure:
            return read_structure(document).identity.id;
        case DocumentType::Material:
            return read_material(document).identity.id;
        case DocumentType::Instance:
            return read_instance(document).instance_id;
    }
    return std::string();
}

std::vector<std::string> ResourceRegistry::dependency_refs(const Document& document) const {
    std::vector<std::string> refs;
    if (document.type == DocumentType::Structure) {
        StructureDefinition structure = read_structure(document);
        refs = structure.atom_refs();
        if (structure.references.is_map()) {
            const Value* subs = structure.references.field("Substructures");
            if (subs != nullptr && subs->is_list()) {
                for (const auto& ref : subs->items()) refs.push_back(ref.scalar_text());
            }
        }
    } else if (document.type == DocumentType::Material) {
        MaterialDefinition material = read_material(document);
        refs = material.structure_refs();
        if (material.references.is_map()) {
            const Value* atoms = material.references.field("AtomDefinitions");
            if (atoms != nullptr && atoms->is_list()) {
                for (const auto& ref : atoms->items()) refs.push_back(ref.scalar_text());
            }
        }
    } else if (document.type == DocumentType::Instance) {
        MaterialInstance instance = read_instance(document);
        if (!instance.definition_ref.empty()) refs.push_back(instance.definition_ref);
        for (const auto& component : instance.components) refs.push_back(component.material_ref);
    }
    std::vector<std::string> seen;
    for (const auto& ref : refs) {
        if (!ref.empty() && std::find(seen.begin(), seen.end(), ref) == seen.end()) seen.push_back(ref);
    }
    return seen;
}

std::string ResourceRegistry::canonical_key(const std::string& ref) const {
    auto cached = cache_.find(ref);
    if (cached != cache_.end()) return ref;
    auto by_id = by_id_.find(ref);
    if (by_id != by_id_.end()) return by_id->second;
    auto by_path = by_path_.find(ref);
    if (by_path != by_path_.end()) return by_path->second;
    if (resolver_) {
        std::string key = resolver_(ref);
        if (!key.empty()) return key;
    }
    return std::string();
}

bool ResourceRegistry::has(const std::string& ref) const { return !canonical_key(ref).empty(); }

const Document* ResourceRegistry::get(const std::string& ref) const {
    std::string key = canonical_key(ref);
    if (key.empty()) return nullptr;
    auto it = cache_.find(key);
    return it == cache_.end() ? nullptr : &it->second;
}

std::vector<std::string> ResourceRegistry::keys() const {
    std::vector<std::string> result;
    result.reserve(cache_.size());
    for (const auto& entry : cache_) result.push_back(entry.first);
    return result;
}

std::vector<std::string> ResourceRegistry::logical_paths() const {
    std::vector<std::string> result;
    result.reserve(by_path_.size());
    for (const auto& entry : by_path_) result.push_back(entry.first);
    std::sort(result.begin(), result.end());
    return result;
}

std::vector<std::string> ResourceRegistry::sorted_ids() const {
    std::vector<std::string> result;
    result.reserve(by_id_.size());
    for (const auto& entry : by_id_) result.push_back(entry.first);
    std::sort(result.begin(), result.end());
    return result;
}

std::size_t ResourceRegistry::size() const { return cache_.size(); }

bool ResourceRegistry::has_key(const std::string& key) const { return cache_.find(key) != cache_.end(); }

std::string ResourceRegistry::key_for_path(const std::string& logical_path) const {
    auto it = by_path_.find(logical_path);
    return it == by_path_.end() ? std::string() : it->second;
}

void ResourceRegistry::walk(const std::string& key, std::map<std::string, std::vector<std::string>>& graph,
                            std::vector<std::string>& visiting, bool recursive) const {
    if (graph.count(key)) return;
    auto found = std::find(visiting.begin(), visiting.end(), key);
    if (found != visiting.end()) {
        std::vector<std::string> cycle(found, visiting.end());
        cycle.push_back(key);
        std::string message = "cyclic dependency: ";
        for (std::size_t i = 0; i < cycle.size(); ++i) {
            if (i != 0) message += " -> ";
            message += cycle[i];
        }
        throw CyclicDependencyError(message);
    }
    visiting.push_back(key);
    auto it = cache_.find(key);
    if (it == cache_.end()) throw ResourceNotFound("resource not found: " + key);
    std::vector<std::string> child_keys;
    for (const auto& raw : dependency_refs(it->second)) {
        std::string child = canonical_key(raw);
        if (child.empty()) {
            child_keys.push_back(raw);
            continue;
        }
        child_keys.push_back(child);
        if (recursive) walk(child, graph, visiting, recursive);
    }
    graph[key] = child_keys;
    visiting.pop_back();
}

std::map<std::string, std::vector<std::string>> ResourceRegistry::dependencies(const std::string& ref,
                                                                                bool recursive) const {
    std::string root = canonical_key(ref);
    if (root.empty()) throw ResourceNotFound("resource not found: " + ref);
    std::map<std::string, std::vector<std::string>> graph;
    std::vector<std::string> visiting;
    walk(root, graph, visiting, recursive);
    return graph;
}

std::map<std::string, std::vector<std::string>> ResourceRegistry::missing_references() const {
    std::map<std::string, std::vector<std::string>> missing;
    for (const auto& entry : cache_) {
        std::vector<std::string> unresolved;
        for (const auto& ref : dependency_refs(entry.second)) {
            if (canonical_key(ref).empty()) unresolved.push_back(ref);
        }
        if (!unresolved.empty()) missing[entry.first] = unresolved;
    }
    return missing;
}

void ResourceRegistry::check_cycles() const {
    for (const auto& entry : cache_) {
        try {
            dependencies(entry.first);
        } catch (const ResourceNotFound&) {
            continue;
        }
    }
}

std::vector<std::string> ResourceRegistry::dependents(const std::string& ref) const {
    std::string target = canonical_key(ref);
    if (target.empty()) throw ResourceNotFound("resource not found: " + ref);
    std::set<std::string> result;
    for (const auto& entry : cache_) {
        std::map<std::string, std::vector<std::string>> graph;
        try {
            graph = dependencies(entry.first);
        } catch (const ResourceNotFound&) {
            continue;
        } catch (const CyclicDependencyError&) {
            continue;
        }
        std::set<std::string> reachable;
        std::vector<std::string> stack{entry.first};
        while (!stack.empty()) {
            std::string node = stack.back();
            stack.pop_back();
            auto it = graph.find(node);
            if (it == graph.end()) continue;
            for (const auto& child : it->second) {
                if (reachable.insert(child).second) stack.push_back(child);
            }
        }
        if (reachable.count(target)) result.insert(entry.first);
    }
    result.erase(target);
    return std::vector<std::string>(result.begin(), result.end());
}

}  // namespace ums
