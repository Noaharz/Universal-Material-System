# Versioning

## 1. Version field

Every definition carries an integer `Version` at the top level, starting at `1`.
Versions must be present and `>= 1`.

## 2. Compatibility rules

* A minor, backwards-compatible change (adding optional fields) may keep the
  same major version.
* A breaking change (removing/renaming required fields, changing meaning or
  units of a value) increments the version.
* References never encode a version in the path; the resource manager resolves
  the version that is present in the library.

## 2.1 Additive sections

The `Appearance` and `Contact` sections (and `ContactPairs`) were added as
optional, backwards-compatible sections. Documents that do not use them stay at
`Version: 1`. Unknown sections and unknown fields are preserved on load and
written back on save, so a newer writer does not silently drop data that an
older reader does not understand.

## 3. Controlled updates

When a definition changes:

1. The version is incremented.
2. Re-validation is triggered.
3. Dependent resources (see the dependency graph) are re-resolved.
4. Cached instances that pinned the previous version may be invalidated
   explicitly.

The resource manager exposes `clear_cache()` for a controlled reload.
