"""Shared pytest configuration for the launcher tests.

The folder exists so that `pytest launcher release` can collect it. The
launcher imports `core.startup` from the backend code folder, so `backend/`
and `launcher/` are put on `sys.path` here, as `start.pyw` does at startup
(plan section 9.5, step 1).
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

for _folder in (_REPO_ROOT / "launcher", _REPO_ROOT / "backend"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))
