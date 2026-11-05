"""Process environment flags shared by settings and configuration."""

import os


def debug_enabled():
    """True only when CARDFACTORY_DEBUG, without surrounding whitespace, is "1"."""
    return os.environ.get("CARDFACTORY_DEBUG", "").strip() == "1"
