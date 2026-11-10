"""Deterministic card validators: pure functions, no Django and no provider (see spec RN-14).
Details: specs/plan.md, sections 3 and 5.
"""

from validators.composition import validate
from validators.result import Cause, ValidationResult

__all__ = ["Cause", "ValidationResult", "validate"]
