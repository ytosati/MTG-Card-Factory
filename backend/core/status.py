"""Status of the configuration and the reference database, without any key value.
Details: specs/plan.md, sections 6 and 8.
"""

import logging
from dataclasses import dataclass

from django.conf import settings
from django.db import DatabaseError

from catalog.selectors import is_ready, list_sources
from core.config import get_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusSnapshot:
    """What the status reports; keys appear only as a boolean."""

    text_provider: str | None
    text_model: str | None
    text_key_configured: bool
    image_provider: str | None
    image_model: str | None
    settings: tuple
    next_start_port: int | None
    database_ready: bool
    sources: tuple


def settings_list(config):
    """The settings to fix and the notices, as the status and the setup show them (see spec RN-08, RN-28)."""
    return config.settings_to_fix + config.notices


def status_snapshot():
    """The current configuration, read again when `.env` changed (see spec RN-08)."""
    config = get_config()
    # The port is read once at startup; a different value applies at the next start (see spec RN-47).
    # An unreadable file says nothing about the port (see spec CA-77).
    port_changed = not config.unreadable and config.app_port != settings.RUNNING_PORT
    next_start_port = config.app_port if port_changed else None
    database_ready, sources = _database_state()
    return StatusSnapshot(
        text_provider=config.llm_provider or None,
        text_model=config.llm_model or None,
        text_key_configured=bool(config.llm_api_key),
        image_provider=config.image_provider or None,
        image_model=config.image_model or None,
        settings=settings_list(config),
        next_start_port=next_start_port,
        database_ready=database_ready,
        sources=sources,
    )


def _database_state():
    """(readiness, source records); a database that cannot be read is not ready, so Status still opens."""
    try:
        return is_ready(), tuple(list_sources())
    except DatabaseError:
        logger.exception("The status could not read the reference database.")
        return False, ()
