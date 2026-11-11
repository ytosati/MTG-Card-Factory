"""Scriptable fake text adapter for tests; never selectable from .env.

Details: specs/plan.md, section 9.2.
"""

import copy
from dataclasses import dataclass
from typing import Any

from providers.base import Usage
from providers.errors import InvalidResponse
from providers.schema import validate_json


@dataclass(frozen=True)
class FakeCall:
    """One call received by the fake, with a copy of its arguments as given."""

    system: str
    messages: list[dict[str, str]]
    schema: dict[str, Any]


class FakeTextAdapter:
    """Answers each call with the next script entry: a (data, Usage) pair or an exception to raise."""

    def __init__(self, script: list[Any] | None = None):
        self._script: list[Any] = list(script or [])
        self.calls: list[FakeCall] = []

    def add_response(self, data: Any, usage: Usage) -> None:
        self._script.append((data, usage))

    def add_error(self, error: Exception) -> None:
        self._script.append(error)

    def complete_json(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> tuple[Any, Usage]:
        # Copies, so a caller that later extends its conversation does not rewrite the record.
        self.calls.append(
            FakeCall(system=system, messages=copy.deepcopy(messages), schema=copy.deepcopy(schema))
        )
        # AssertionError, not a ProviderError: an unscripted call is a test mistake.
        if not self._script:
            raise AssertionError("FakeTextAdapter received a call with no scripted entry left.")
        entry = self._script.pop(0)
        if isinstance(entry, BaseException):
            raise entry
        data, usage = entry
        # Checked like a real adapter does, so callers never receive data off the schema.
        if validate_json(data, schema):
            raise InvalidResponse("The response does not match the requested format.", usage=usage)
        return data, usage
