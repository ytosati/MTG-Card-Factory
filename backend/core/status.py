"""Status of the configuration, without any key value.
Details: specs/plan.md, sections 6 and 8.
"""

from dataclasses import dataclass

from django.conf import settings

from core.config import get_config


@dataclass(frozen=True)
class StatusSnapshot:
    """What the status reports about the configuration; keys appear only as a boolean."""

    text_provider: str | None
    text_model: str | None
    text_key_configured: bool
    image_provider: str | None
    image_model: str | None
    settings: tuple
    next_start_port: int | None


def status_snapshot():
    """The current configuration, read again when `.env` changed (see spec RN-08)."""
    config = get_config()
    # The port is read once at startup; a different value applies at the next start (see spec RN-47).
    # An unreadable file says nothing about the port (see spec CA-77).
    port_changed = not config.unreadable and config.app_port != settings.RUNNING_PORT
    next_start_port = config.app_port if port_changed else None
    return StatusSnapshot(
        text_provider=config.llm_provider or None,
        text_model=config.llm_model or None,
        text_key_configured=bool(config.llm_api_key),
        image_provider=config.image_provider or None,
        image_model=config.image_model or None,
        settings=config.settings_to_fix + config.notices,
        next_start_port=next_start_port,
    )
