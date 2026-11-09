"""Logging filter that removes the API keys from every record.
Details: specs/plan.md, section 8 ("Key protection").
"""

import logging
import threading
from collections.abc import Mapping

from core.config import get_config

MARKER = "***"
# Shorter values would replace ordinary words (see specs/plan.md, section 8, and spec RN-06).
MIN_KEY_LENGTH = 8

# Every key value read from the configuration since the process started, shared
# by all filter instances, so a key replaced in `.env` stays redacted even when a
# call read it before any record was logged. Kept in memory only (spec RN-06).
# Looked up by name on each use, never bound elsewhere, so it can be replaced as a whole.
_seen_keys = set()
_seen_keys_lock = threading.Lock()


class KeyRedactionFilter(logging.Filter):
    """Replaces every key value read in the process with `***` in the message, traceback and stack."""

    def filter(self, record):
        keys = _keys_to_redact()
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


def remember_keys(config):
    """Add the key values of `config` long enough to redact; core.config calls it on every read."""
    values = (
        secret.reveal()
        for secret in (config.llm_api_key, config.image_api_key, config.ignored_image_api_key)
    )
    long_enough = {value for value in values if len(value) >= MIN_KEY_LENGTH}
    with _seen_keys_lock:
        _seen_keys.update(long_enough)


def _keys_to_redact():
    """Current and earlier key values, longest first so a key inside another never survives."""
    try:
        # Reading the configuration remembers its keys (remember_keys).
        get_config()
    except Exception:
        # Logging must keep working even when the configuration cannot be read.
        pass
    with _seen_keys_lock:
        return tuple(sorted(_seen_keys, key=len, reverse=True))


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
