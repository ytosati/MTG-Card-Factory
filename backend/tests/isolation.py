"""Early pytest plugin: gives the whole test session a temporary application home.

Loaded with `-p tests.isolation` (pytest.ini), so this module runs before
pytest-django imports the settings in its pytest_load_initial_conftests hook.
"""

import atexit
import os
import shutil
import tempfile
from pathlib import Path

from tests.project_environment import is_project_variable


def _clear_project_environment():
    # DJANGO_SETTINGS_MODULE is cleared too, so pytest-django takes it from pytest.ini.
    for name in list(os.environ):
        if is_project_variable(name):
            del os.environ[name]


_clear_project_environment()

TEST_HOME = Path(tempfile.mkdtemp(prefix="cardfactory-test-home-")).resolve()
(TEST_HOME / "data").mkdir()
os.environ["CARDFACTORY_HOME"] = str(TEST_HOME)


def _remove_test_home():
    shutil.rmtree(TEST_HOME, ignore_errors=True)


# A startup failure (for example in pytest-django) skips pytest_unconfigure.
atexit.register(_remove_test_home)


# Database names as configured, before pytest-django swaps them for test databases.
CONFIGURED_DATABASE_NAMES = {}


def pytest_configure(config):
    """Record the configured database names; pytest-django has loaded the settings by now."""
    try:
        from django.conf import settings

        databases = settings.DATABASES
    except Exception:
        # Without Django settings there is nothing to record.
        return
    for alias, database in databases.items():
        CONFIGURED_DATABASE_NAMES[alias] = database.get("NAME")


def pytest_unconfigure(config):
    """Remove the temporary home once the session ends."""
    try:
        from django.db import connections

        connections.close_all()
    except Exception:
        # Django may be missing or not configured; the folder is still removed.
        pass
    _remove_test_home()
