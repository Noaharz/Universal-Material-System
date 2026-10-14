"""Exception hierarchy for the Universal Material System."""

from __future__ import annotations


class UmsError(Exception):
    """Base class for all UMS errors."""


class ParseError(UmsError):
    """Raised when a document cannot be tokenized or parsed."""

    def __init__(self, message: str, *, line: int | None = None, path: str | None = None):
        self.line = line
        self.path = path
        location = ""
        if path:
            location += f" in {path}"
        if line is not None:
            location += f" (line {line})"
        super().__init__(f"{message}{location}")


class UnitError(UmsError):
    """Raised for unknown units or incompatible dimensional operations."""


class ValidationError(UmsError):
    """Raised when a definition fails validation in strict mode."""


class ReferenceError_(UmsError):
    """Raised when a resource reference cannot be resolved structurally."""


class ResourceNotFound(ReferenceError_):
    """Raised when a referenced resource does not exist in any search path."""


class CyclicDependencyError(ReferenceError_):
    """Raised when an illegal dependency cycle is detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        chain = " -> ".join(cycle)
        super().__init__(f"cyclic dependency detected: {chain}")
