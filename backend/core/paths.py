"""Application home and data folder: the only place that resolves them.
Details: specs/plan.md, section 7.
"""

import os
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def app_home():
    """Absolute path of the folder that holds `.env` and `data/`."""
    # Read on every call, not at import: the launcher and the tests set the
    # variable, and a relative value follows the current working directory.
    value = os.environ.get("CARDFACTORY_HOME", "").strip()
    if not value:
        return REPOSITORY_ROOT
    return Path(os.path.abspath(value))


def data_dir():
    """Absolute path of the runtime data folder under the application home."""
    return app_home() / "data"
