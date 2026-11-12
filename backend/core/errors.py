"""The error envelope shared by API answers and stored jobs.
Details: specs/plan.md, section 6.
"""

import sqlite3


# Every error code of plan section 6, and the settings-list codes; no other module spells them.
CODE_CONFIG_INVALID = "config_invalid"
CODE_IGNORED = "ignored"
CODE_ORIGIN_REFUSED = "origin_refused"
CODE_NOT_FOUND = "not_found"
CODE_METHOD_NOT_ALLOWED = "method_not_allowed"
CODE_VALIDATION = "validation"
CODE_DATABASE_NOT_READY = "database_not_ready"
CODE_DATABASE_BUSY = "database_busy"
CODE_INSUFFICIENT_SPACE = "insufficient_space"
CODE_SOURCE_UNREACHABLE = "source_unreachable"
CODE_AUTH = "auth"
CODE_QUOTA = "quota"
CODE_RATE_LIMITED = "rate_limited"
CODE_MODEL_NOT_FOUND = "model_not_found"
CODE_PROVIDER_UNAVAILABLE = "provider_unavailable"
CODE_PROVIDER_REJECTED = "provider_rejected"
CODE_PROVIDER_NOT_AVAILABLE_YET = "provider_not_available_yet"
CODE_INVALID_RESPONSE = "invalid_response"
CODE_CONTENT_REFUSED = "content_refused"
CODE_ART_UNAVAILABLE = "art_unavailable"
CODE_CARD_CHANGED = "card_changed"
CODE_GENERATION_RUNNING = "generation_running"
CODE_BAD_REQUEST = "bad_request"
CODE_INTERNAL = "internal"

INTERNAL_MESSAGE = "Something went wrong in Card Factory. Try again."
DATABASE_BUSY_MESSAGE = "The database is busy with another task. Wait a moment and try again."


def error_body(code, message, setting=None, fields=None):
    """The envelope `{"error": {code, message, setting, fields}}`."""
    return {"error": {"code": code, "message": message, "setting": setting, "fields": fields}}


class MappedError(Exception):
    """A failure with an error code of plan section 6 and a fixed message that is safe to show."""

    def __init__(self, code, message, setting=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.setting = setting


def database_busy_error(error):
    """The `database_busy` MappedError of an OperationalError for a locked database, else None (plan section 7)."""
    # Imported here so core.config can import the codes without Django settings.
    from django.db import OperationalError

    if not isinstance(error, OperationalError):
        return None
    code = getattr(error.__cause__, "sqlite_errorcode", None)
    if isinstance(code, int):
        # The low byte is the primary result code; extended codes share it.
        busy = code & 0xFF == sqlite3.SQLITE_BUSY
    else:
        busy = "database is locked" in str(error).lower()
    return MappedError(CODE_DATABASE_BUSY, DATABASE_BUSY_MESSAGE) if busy else None
