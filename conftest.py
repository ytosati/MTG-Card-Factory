"""Applies the backend network guard to `pytest launcher release` (see spec RN-29, CA-19).

Loaded by file path under its own module name, so the `tests` folders never collide.
"""

import importlib.util
import sys
from pathlib import Path

_GUARD_PATH = Path(__file__).resolve().parent / "backend" / "tests" / "network_guard.py"
_GUARD_NAME = "cardfactory_network_guard"


def _load_guard():
    if _GUARD_NAME in sys.modules:
        return sys.modules[_GUARD_NAME]
    spec = importlib.util.spec_from_file_location(_GUARD_NAME, _GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[_GUARD_NAME] = module
    spec.loader.exec_module(module)
    return module


network_guard = _load_guard()


def pytest_configure(config):
    if not config.pluginmanager.is_registered(network_guard):
        config.pluginmanager.register(network_guard, _GUARD_NAME)
