"""Parser for the UMS text formats.

All three resource formats share a single, indentation-based document grammar.
A document starts with an upper-case type keyword (``ATOM``, ``STRUCTURE``,
``MATERIAL`` or ``INSTANCE``) followed by a sequence of named sections::

    STRUCTURE

    Version: 1

    Identity:
        Id: "structure.water"
        Name: "Water"
        StructureType: Molecular

    Composition:
        - AtomRef: "elements/hydrogen.atom"
          Count: 2

The grammar is a strict subset of YAML: nested mappings by indentation, lists
introduced by ``- `` and flow sequences ``[a, b, c]``. Scalars are interpreted
conservatively - quoted strings stay strings, bare numbers become int/float and
quantities such as ``3.567 angstrom`` stay raw text so the semantic layer can
attach explicit units.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass
from typing import Any, List, Tuple

from .errors import ParseError
from .units import Quantity, try_quantity


class DocumentType(enum.Enum):
    ATOM = "ATOM"
    STRUCTURE = "STRUCTURE"
    MATERIAL = "MATERIAL"
    INSTANCE = "INSTANCE"  # material instance / scene fragment

    @classmethod
    def from_token(cls, token: str) -> "DocumentType":
        normalized = token.strip().upper()
        for member in cls:
            if member.value == normalized:
                return member
        aliases = {"MOLECULE": cls.STRUCTURE, "MATERIALINSTANCE": cls.INSTANCE}
        if normalized in aliases:
            return aliases[normalized]
        raise ParseError(f"unknown document type keyword: {token!r}")


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?$")


@dataclass
class _Line:
    indent: int
    text: str
    number: int


def _prepare(text: str) -> List[_Line]:
    lines: List[_Line] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        raw = raw.rstrip("\r")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        expanded = raw.replace("\t", "    ")
        indent = len(expanded) - len(expanded.lstrip(" "))
        lines.append(_Line(indent, expanded.strip(), number))
    return lines


def parse_scalar(text: str) -> Any:
    """Parse a bare scalar token into a Python value."""
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "none", "~"):
        return None
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _split_key(text: str) -> Tuple[str, str] | None:
    """Split ``Key: value`` at the first top-level colon."""
    quote: str | None = None
    for idx, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == ":":
            return text[:idx].strip(), text[idx + 1:].strip()
    return None


def _parse_flow_list(text: str) -> List[Any]:
    inner = text[1:-1].strip()
    if not inner:
        return []
    items: List[Any] = []
    depth = 0
    quote: str | None = None
    current = ""
    for ch in inner:
        if quote:
            current += ch
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            current += ch
        elif ch in "[{":
            depth += 1
            current += ch
        elif ch in "]}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            items.append(parse_scalar(current))
            current = ""
        else:
            current += ch
    if current.strip():
        items.append(parse_scalar(current))
    return items


def _parse_inline(text: str) -> Any:
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        return _parse_flow_list(text)
    return parse_scalar(text)


class _BlockParser:
    def __init__(self, lines: List[_Line], path: str | None = None):
        self.lines = lines
        self.path = path
        self.i = 0

    def _current(self) -> _Line | None:
        return self.lines[self.i] if self.i < len(self.lines) else None

    def parse(self) -> Any:
        line = self._current()
        if line is None:
            return {}
        return self._block(line.indent)

    def _block(self, indent: int) -> Any:
        line = self._current()
        if line is None:
            return {}
        if line.text.startswith("- "):
            return self._list(indent)
        return self._mapping(indent)

    def _list(self, indent: int) -> List[Any]:
        items: List[Any] = []
        while True:
            line = self._current()
            if line is None or line.indent < indent or not line.text.startswith("- "):
                break
            if line.indent > indent:
                raise ParseError("unexpected indentation in list", line=line.number, path=self.path)
            content = line.text[2:].strip()
            self.i += 1
            if content == "":
                nxt = self._current()
                if nxt is not None and nxt.indent > indent:
                    items.append(self._block(nxt.indent))
                else:
                    items.append(None)
                continue
            kv = _split_key(content)
            if kv is not None:
                item: dict[str, Any] = {}
                key, rest = kv
                if rest == "":
                    nxt = self._current()
                    if nxt is not None and nxt.indent > indent:
                        item[key] = self._block(nxt.indent)
                    else:
                        item[key] = None
                else:
                    item[key] = _parse_inline(rest)
                nxt = self._current()
                if nxt is not None and nxt.indent > indent:
                    extra = self._mapping(nxt.indent)
                    item.update(extra)
                items.append(item)
            else:
                items.append(_parse_inline(content))
                nxt = self._current()
                if nxt is not None and nxt.indent > indent:
                    raise ParseError("scalar list items cannot have children", line=nxt.number, path=self.path)
        return items

    def _mapping(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while True:
            line = self._current()
            if line is None or line.indent < indent:
                break
            if line.indent > indent:
                raise ParseError("unexpected indentation", line=line.number, path=self.path)
            if line.text.startswith("- "):
                break
            kv = _split_key(line.text)
            if kv is None:
                raise ParseError(f"expected 'Key: value', got {line.text!r}", line=line.number, path=self.path)
            key, rest = kv
            if not key:
                raise ParseError("empty key", line=line.number, path=self.path)
            self.i += 1
            if rest == "":
                nxt = self._current()
                if nxt is not None and nxt.indent > indent:
                    result[key] = self._block(nxt.indent)
                else:
                    result[key] = None
            else:
                result[key] = _parse_inline(rest)
        return result


def parse_document(text: str, path: str | None = None) -> Tuple[DocumentType, dict]:
    """Parse a UMS document, returning ``(document_type, sections)``."""
    lines = _prepare(text)
    if not lines:
        raise ParseError("empty document", path=path)
    first = lines[0]
    if first.indent != 0:
        raise ParseError("document type keyword must not be indented", line=first.number, path=path)
    doc_type = DocumentType.from_token(first.text)
    body = lines[1:]
    if not body:
        return doc_type, {}
    sections = _BlockParser(body, path).parse()
    if not isinstance(sections, dict):
        raise ParseError("document body must be a mapping of sections", path=path)
    return doc_type, sections


def coerce_quantity(value: Any) -> Quantity | None:
    """Interpret a parsed scalar as a :class:`Quantity` when possible."""
    if value is None:
        return None
    return try_quantity(value)
