"""What identifies this Card Factory on its port (see spec RN-47).
Details: specs/plan.md, section 6 (instance contract).
"""

from dataclasses import dataclass

from core.paths import app_home

APP_NAME = "card-factory"
UNKNOWN_VERSION = "0.0.0+unknown"


@dataclass(frozen=True)
class InstanceSnapshot:
    """The instance contract: these fields never change meaning between versions."""

    app: str
    version: str
    home: str


def instance_snapshot():
    """The application name, the version from `VERSION` in the home, and the home."""
    home = app_home()
    return InstanceSnapshot(app=APP_NAME, version=_read_version(home / "VERSION"), home=str(home))


def _read_version(path):
    try:
        version = path.read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeDecodeError):
        return UNKNOWN_VERSION
    return version or UNKNOWN_VERSION
