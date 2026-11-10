"""Text adapter protocol and the usage value every provider call reports.

Details: specs/plan.md, section 9.2.
"""

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Usage:
    """Tokens a provider reported for one call (see spec RN-09)."""

    input_tokens: int
    output_tokens: int


@runtime_checkable
class TextAdapter(Protocol):
    """A text provider that answers with JSON matching a schema."""

    def complete_json(
        self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]
    ) -> tuple[Any, Usage]:
        """Return the parsed JSON response, already checked against `schema`, and its usage."""
        ...
