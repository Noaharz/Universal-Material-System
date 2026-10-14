# Format Grammar

All three UMS formats share one indentation-based document grammar (a strict
subset of YAML).

## 1. Document

```
<DOCTYPE>

<section>:
    <key>: <value>
    ...
```

* The first non-empty, non-comment line is the **document type keyword**:
  `ATOM`, `STRUCTURE`, `MATERIAL` or `INSTANCE`. It must not be indented.
* The remainder is a mapping of **sections** at indentation level 0.
* Blank lines are ignored. A line whose first non-space character is `#` is a
  comment.
* Indentation is by spaces only; tabs are expanded to four spaces. Siblings must
  share the same indentation; nesting is expressed by deeper indentation.

## 2. Values

| Kind | Syntax | Parsed as |
| --- | --- | --- |
| Integer | `Version: 1` | `int` |
| Float | `Ratio: 0.008` | `float` |
| Boolean | `PeriodicAxes: [true, false, true]` | `bool` |
| String | `Name: Water` | `str` |
| Quoted string | `Id: "element.gold"` | `str` |
| Quantity | `AtomicMass: 196.96657 u` | `Quantity` (value + unit) |
| Flow list | `[true, true, true]` | `list` |
| Special | `parameterized` | `str` (kept verbatim) |

## 3. Mappings

```
Identity:
    Id: "structure.water"
    Name: "Water"
    StructureType: Molecular
```

## 4. Sequences

Sequence items are introduced by `- `. Items may be scalars or mappings. For a
mapping item the first key is on the `- ` line and the remaining keys are
indented one level deeper:

```
Composition:
    - AtomRef: "elements/hydrogen.atom"
      Count: 2

    - AtomRef: "elements/oxygen.atom"
      Count: 1
```

## 5. Colons inside values

Splitting happens at the first top-level `:` outside quotes. Values that contain
a colon (URIs, references) must be quoted: `DataSource: "doi:10.1000/xyz"`.

## 6. Serialization

The canonical serializer emits four-space indentation, one blank line after the
type keyword and quoted strings whenever a scalar could be misread (contains
`.`, `/`, `:`, whitespace, is numeric-like or a reserved word).
