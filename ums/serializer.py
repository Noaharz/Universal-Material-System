"""Serialize sections back to the UMS indentation grammar.

Used for round-tripping, formatting and deterministic test fixtures.
"""

from __future__ import annotations

from typing import Any, List

from .parser import DocumentType
from .units import Quantity, try_quantity

_SPECIAL_CHARS = set(".,/:{}[]#&*!|>'\"%@`\t ")


def _needs_quote(text: str) -> bool:
    if text == "":
        return True
    if text[0] in "-?":  # ambiguous scalar indicators
        return True
    if try_quantity(text) is not None:  # e.g. "196.96657 u" is a quantity, not text
        return False
    for ch in text:
        if ch in _SPECIAL_CHARS:
            return True
    lowered = text.lower()
    if lowered in ("true", "false", "null", "none", "~"):
        return True
    try:
        float(text)
        return True
    except ValueError:
        return False


def format_scalar(value: Any) -> str:
    if isinstance(value, Quantity):
        if value.unit.symbol in ("", "1", "dimensionless"):
            return f"{value.value:g}"
        return f"{value.value:g} {value.unit.symbol}"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"{value:g}" if isinstance(value, float) else str(value)
    text = str(value)
    if _needs_quote(text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _emit_mapping(mapping: dict, indent: int, out: List[str]) -> None:
    pad = " " * indent
    for key, value in mapping.items():
        if isinstance(value, (dict, list)) and value:
            out.append(f"{pad}{key}:")
            _emit_value(value, indent + 4, out)
        elif isinstance(value, (dict, list)):
            out.append(f"{pad}{key}:")
            _emit_value({} if isinstance(value, dict) else [], indent + 4, out)
        else:
            out.append(f"{pad}{key}: {format_scalar(value)}")


def _emit_sequence(items: list, indent: int, out: List[str]) -> None:
    pad = " " * indent
    for item in items:
        if isinstance(item, dict) and item:
            first_key = next(iter(item))
            first_value = item[first_key]
            keys = list(item.keys())
            if isinstance(first_value, (dict, list)) and first_value:
                out.append(f"{pad}- {first_key}:")
                _emit_value(first_value, indent + 4, out)
            else:
                out.append(f"{pad}- {first_key}: {format_scalar(first_value)}")
            rest = {k: item[k] for k in keys[1:]}
            if rest:
                _emit_mapping(rest, indent + 2, out)
        elif isinstance(item, dict):
            out.append(f"{pad}-")
        elif isinstance(item, list):
            out.append(f"{pad}-")
            _emit_value(item, indent + 2, out)
        else:
            out.append(f"{pad}- {format_scalar(item)}")


def _emit_value(value: Any, indent: int, out: List[str]) -> None:
    if isinstance(value, dict):
        _emit_mapping(value, indent, out)
    elif isinstance(value, list):
        _emit_sequence(value, indent, out)


def serialize_document(doc_type: DocumentType, sections: dict) -> str:
    lines: List[str] = [doc_type.value, ""]
    _emit_mapping(sections, 0, lines)
    return "\n".join(lines) + "\n"
