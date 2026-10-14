#include "ums/library.hpp"

#ifndef UMS_NO_FILESYSTEM

#include <algorithm>
#include <filesystem>

#include "ums/fileio.hpp"
#include "ums/reader.hpp"

namespace fs = std::filesystem;

namespace ums {

namespace {

std::string to_lower(std::string text) {
    std::transform(text.begin(), text.end(), text.begin(), [](unsigned char ch) {
        return static_cast<char>(std::tolower(ch));
    });
    return text;
}

std::string relative_logical(const std::string& file, const std::string& base) {
    std::error_code error;
    auto relative = fs::relative(file, base, error);
    if (!error && !relative.empty() && relative.string().rfind("..", 0) != 0) {
        return relative.generic_string();
    }
    return std::string();
}

}  // namespace

ResourceLibrary::ResourceLibrary(std::vector<std::string> search_paths) {
    for (auto& path : search_paths) add_search_path(path);
    registry_.set_resolver([this](const std::string& ref) { return resolve_path(ref); });
}

void ResourceLibrary::add_search_path(const std::string& path) {
    std::string normalized = fs::path(path).lexically_normal().string();
    if (std::find(paths_.begin(), paths_.end(), normalized) == paths_.end()) {
        paths_.push_back(normalized);
    }
    indexed_ = false;
}

std::string ResourceLibrary::resource_id(const Document& document) const {
    return registry_.resource_id(document);
}

std::vector<std::string> ResourceLibrary::dependency_refs(const Document& document) const {
    return registry_.dependency_refs(document);
}

void ResourceLibrary::index(bool force) {
    if (indexed_ && !force) return;

    std::vector<std::string> discovered;
    for (const auto& base : paths_) {
        if (!fs::is_directory(base)) continue;
        for (auto it = fs::recursive_directory_iterator(base); it != fs::recursive_directory_iterator(); ++it) {
            if (!it->is_regular_file()) continue;
            if (!is_document_suffix(it->path().extension().string())) continue;
            discovered.push_back(it->path().string());
        }
    }
    std::sort(discovered.begin(), discovered.end());

    for (const auto& file : discovered) {
        std::string logical;
        for (const auto& base : paths_) {
            logical = relative_logical(file, base);
            if (!logical.empty()) break;
        }
        if (logical.empty()) logical = file;
        try {
            Document document = parse_file(file);
            registry_.add(file, logical, std::move(document));
        } catch (const std::exception&) {
            continue;
        }
    }
    indexed_ = true;
}

std::string ResourceLibrary::load_file(const std::string& file_path) {
    for (const auto& base : paths_) {
        std::string rel = relative_logical(file_path, base);
        if (!rel.empty()) {
            std::string existing = registry_.key_for_path(rel);
            if (!existing.empty()) return existing;
        }
    }
    if (registry_.has_key(file_path)) return file_path;
    Document document;
    try {
        document = parse_file(file_path);
    } catch (const std::exception&) {
        return std::string();
    }
    std::string logical;
    for (const auto& base : paths_) {
        logical = relative_logical(file_path, base);
        if (!logical.empty()) break;
    }
    registry_.add(file_path, logical, std::move(document));
    return file_path;
}

std::string ResourceLibrary::resolve_path(const std::string& ref) {
    index();
    std::string lowered = to_lower(ref);
    bool path_kind = is_document_suffix(fs::path(lowered).extension().string());
    if (path_kind) {
        for (const auto& base : paths_) {
            fs::path candidate = fs::path(base) / ref;
            if (fs::is_regular_file(candidate)) {
                std::string rel = relative_logical(candidate.string(), base);
                if (!rel.empty()) {
                    std::string existing = registry_.key_for_path(rel);
                    if (!existing.empty()) return existing;
                }
                if (registry_.has_key(candidate.string())) return candidate.string();
                Document document;
                try {
                    document = parse_file(candidate.string());
                } catch (const std::exception&) {
                    return std::string();
                }
                registry_.add(candidate.string(), rel.empty() ? ref : rel, std::move(document));
                return candidate.string();
            }
        }
    } else {
        for (const auto& base : paths_) {
            for (const std::string& suffix : {".atom", ".structure", ".material", ".instance"}) {
                fs::path candidate = fs::path(base) / (ref + suffix);
                if (fs::is_regular_file(candidate)) {
                    return load_file(candidate.string());
                }
            }
        }
    }
    return std::string();
}

bool ResourceLibrary::has(const std::string& ref) { return !registry_.canonical_key(ref).empty(); }

const Document* ResourceLibrary::load(const std::string& ref) { return registry_.get(ref); }

std::vector<std::string> ResourceLibrary::logical_paths() const { return registry_.logical_paths(); }

std::vector<std::string> ResourceLibrary::sorted_ids() const { return registry_.sorted_ids(); }

std::size_t ResourceLibrary::size() const { return registry_.size(); }

}  // namespace ums

#endif  // UMS_NO_FILESYSTEM
