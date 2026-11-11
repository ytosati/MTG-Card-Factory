"""The validation result in the stored format of a version's `validation` field.
Details: specs/plan.md, section 7.
"""

from dataclasses import dataclass

APPROVED = "approved"
REJECTED = "rejected"


@dataclass(frozen=True)
class Cause:
    """Why a check rejected the card: a stable check name, a stable code and a message to show."""

    check: str
    code: str
    message: str

    def to_dict(self):
        return {"check": self.check, "code": self.code, "message": self.message}


@dataclass(frozen=True)
class ValidationResult:
    """The outcome of every check run on a card (see spec RN-14)."""

    checks_run: tuple
    causes: tuple
    skipped: tuple = ()

    @property
    def status(self):
        return REJECTED if self.causes else APPROVED

    def to_dict(self):
        """`{status, checks_run, causes, skipped}`, plain JSON."""
        return {
            "status": self.status,
            "checks_run": list(self.checks_run),
            "causes": [cause.to_dict() for cause in self.causes],
            "skipped": list(self.skipped),
        }
