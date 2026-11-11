"""Readiness gate: the default DRF permission requires a ready reference database (see spec RN-28).
Details: specs/plan.md, section 6.
"""

from rest_framework.permissions import BasePermission

from catalog.selectors import is_ready
from core.errors import CODE_DATABASE_NOT_READY, MappedError

# Imports nothing from rest_framework.views: DRF loads this class while that module initializes.
DATABASE_NOT_READY_MESSAGE = "The reference database is not ready yet. Build it on the Setup screen."


class DatabaseReady(BasePermission):
    """Answers `database_not_ready` until a build of the current catalog version is ready.

    Views that work without the database opt out with `permission_classes = []`.
    """

    def has_permission(self, request, view):
        if not is_ready():
            # Raised, not returned False: DRF would answer its own 403 instead of the envelope.
            raise MappedError(CODE_DATABASE_NOT_READY, DATABASE_NOT_READY_MESSAGE)
        return True
