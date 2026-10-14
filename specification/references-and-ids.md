# References, IDs and the Resource Manager

## 1. No absolute paths

Files must not contain hard-coded absolute paths:

```
C:\MyEngine\Materials\Atoms\oxygen.atom     # invalid
```

Instead use **logical resource paths** or **stable IDs**:

```
elements/oxygen.atom        # logical path
element.oxygen              # stable ID
```

Platform-independent separators (`/`) are required.

## 2. Logical paths vs. IDs

* A stable **ID** identifies a resource (`element.oxygen`).
* A logical **path** locates it within a library (`elements/oxygen.atom`).

The resource manager resolves both to the same definition.

## 3. Resource manager responsibilities

1. Find resources by ID or logical path.
2. Load and parse files.
3. Check versions and schemas.
4. Resolve references.
5. Compute dependencies.
6. Reuse already-loaded resources.
7. Cache resources.
8. Report errors and invalid references.
9. Optionally load asynchronously.
10. Update resources on controlled change.

## 4. Dependency graph

```
water.material
    └── water.structure
          ├── hydrogen.atom
          └── oxygen.atom
```

A resource can be used by many others. Shared definitions are loaded once and
not duplicated in memory.

## 5. Requirements

* Platform-independent paths
* Unique resource identities
* Version management
* Reference checking
* Error handling for missing resources
* Optional redirection to other resource sources
* Support for local and remote libraries

## 6. Central guarantees

* **Caching** — loaded definitions are reused.
* **Dependency checking** — missing/invalid references are detected.
* **Cycle detection** — illegal dependency cycles are prevented (`CyclicDependencyError`).
* **Versioning** — changes to definitions are handled in a controlled way.
* **Memory management** — resources can be loaded, released and reloaded.
* **Thread safety** — concurrent access cannot corrupt resource state.

## 7. Host-resolved (opaque) references

Not every reference points at a UMS definition. A texture `Ref` in the
`Appearance` block may be an engine asset id that UMS cannot know - for example
a UUID. UMS treats such values as **opaque strings**: it stores and validates
their shape but never guesses their meaning.

The host decides how they resolve:

* Provide an `asset_checker` to `Validator` / `ResourceRegistry` to check them.
  An unresolved opaque reference is then an error.
* Without a checker, the reference falls back to the UMS `reference_checker`
  (logical path against the library) and finally to an informational note.

The same mechanism backs `ContactPairs[*].Other`, so engines can point contact
overrides at their own material ids without UMS parsing a foreign format.

## 8. C++ host integration

The C++ reader mirrors this: `ResourceRegistry::set_resolver` and
`Validator(reference_checker, asset_checker)` accept host callbacks, and the
non-throwing `try_parse_document` / `try_parse_buffer` API returns a
`Diagnostic` instead of throwing. See `cpp/include/ums/result.hpp`.
