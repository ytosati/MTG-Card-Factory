"""Validator for the JSON schema subset used in structured provider output.

Details: specs/plan.md, section 9.2. The subset is object (properties,
required), array (items), string, integer, number, boolean and enum.
"""

import math
from typing import Any


def validate_json(data: Any, schema: dict[str, Any]) -> list[str]:
    """Return the problems found in `data`; an empty list means it matches `schema`."""
    problems: list[str] = []
    _check(data, schema, "$", problems)
    return problems


def _check(value: Any, schema: dict[str, Any], path: str, problems: list[str]) -> None:
    expected = schema.get("type")
    if expected is not None and not _has_type(value, expected):
        problems.append(f"{path}: expected {expected}, got {_type_name(value)}")
        return
    if "enum" in schema and not _in_enum(value, schema["enum"]):
        problems.append(f"{path}: value is not one of the allowed values")
        return
    if expected == "object":
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                problems.append(f"{path}: missing required property '{name}'")
        for name, subschema in properties.items():
            if name in value:
                _check(value[name], subschema, f"{path}.{name}", problems)
    elif expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            _check(item, schema["items"], f"{path}[{index}]", problems)


def _has_type(value: Any, expected: str) -> bool:
    # bool is a subclass of int in Python, but JSON booleans are not numbers.
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        if isinstance(value, float):
            # Python's json module parses NaN and Infinity, which are not valid JSON numbers.
            return math.isfinite(value)
        return isinstance(value, int) and not isinstance(value, bool)
    return False


def _in_enum(value: Any, allowed: list[Any]) -> bool:
    # Python treats True == 1; JSON does not, so booleans only match booleans.
    return any(
        value == option and isinstance(value, bool) == isinstance(option, bool) for option in allowed
    )


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number" if math.isfinite(value) else "non-finite number"
    return type(value).__name__
