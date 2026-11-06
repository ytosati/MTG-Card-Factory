"""Logging filter that removes the configured API keys from every record.
Details: specs/plan.md, section 8 ("Key protection").
"""

import logging
from collections.abc import Mapping

from core.config import get_config

MARKER = "***"
# Shorter values would replace ordinary words (see specs/plan.md, section 8, and spec RN-06).
MIN_KEY_LENGTH = 8


class KeyRedactionFilter(logging.Filter):
    """Replaces the text key and the image keys with `***` in the message, traceback and stack."""

    def filter(self, record):
        keys = _current_keys()
        if not keys:
            return True
        _redact_message(record, keys)
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = _redact(record.exc_text, keys)
        if record.stack_info:
            record.stack_info = _redact(record.stack_info, keys)
        return True


def _current_keys():
    """Key values long enough to redact, longest first so a key inside another never survives."""
    try:
        config = get_config()
    except Exception:
        # Logging must keep working even when the configuration cannot be read.
        return ()
    values = {
        secret.reveal()
        for secret in (config.llm_api_key, config.image_api_key, config.ignored_image_api_key)
    }
    return tuple(sorted((value for value in values if len(value) >= MIN_KEY_LENGTH), key=len, reverse=True))


def _redact_message(record, keys):
    try:
        message = record.getMessage()
    except Exception:
        # The handler reports the failure and prints msg and args, so both are redacted as text.
        record.msg = _redact(str(record.msg), keys)
        record.args = _redact_args(record.args, keys)
        return
    redacted = _redact(message, keys)
    if redacted != message:
        record.msg = redacted
        record.args = None


def _redact_args(args, keys):
    if isinstance(args, Mapping):
        return {_redact(str(name), keys): _redact(str(value), keys) for name, value in args.items()}
    if isinstance(args, tuple):
        return tuple(_redact(str(value), keys) for value in args)
    return _redact(str(args), keys)


def _redact(text, keys):
    # Plain replace, not a regex: keys may contain regex characters.
    for key in keys:
        text = text.replace(key, MARKER)
    return text
