"""The test session runs against a temporary application home (task T1, spec RN-29)."""

import os
from pathlib import Path

from tests.isolation import TEST_HOME
from tests.project_environment import is_project_variable
from tests.settings_probe import REPOSITORY_ROOT


def _is_under(path, parent):
    return Path(path).resolve().is_relative_to(Path(parent).resolve())


def test_t1_session_home_is_temporary_and_outside_repository():
    """RN-29 / CA-19 / T1: the session sets CARDFACTORY_HOME to a fresh folder with data/, outside the repository."""
    assert Path(os.environ["CARDFACTORY_HOME"]).resolve() == TEST_HOME
    assert (TEST_HOME / "data").is_dir()
    assert not _is_under(TEST_HOME, REPOSITORY_ROOT)


def test_t1_session_environment_has_no_developer_configuration():
    """RN-29 / CA-19 / T1: provider and port variables from the developer's shell are cleared for the session."""
    expected = {"CARDFACTORY_HOME", "DJANGO_SETTINGS_MODULE"}
    leaked = [
        name for name in os.environ if is_project_variable(name) and name.upper() not in expected
    ]
    assert leaked == []


def test_t1_settings_module_comes_from_pytest_ini():
    """RN-29 / CA-19 / T1: after clearing DJANGO_*, pytest-django still loads cardfactory.settings."""
    from django.conf import settings

    assert os.environ.get("DJANGO_SETTINGS_MODULE") == "cardfactory.settings"
    assert settings.SETTINGS_MODULE == "cardfactory.settings"


def test_t1_django_settings_use_the_temporary_home():
    """RN-29 / CA-19 / T1: settings loaded by pytest-django point the database at the temporary home."""
    from django.conf import settings

    database_name = settings.DATABASES["default"]["NAME"]

    assert not _is_under(database_name, REPOSITORY_ROOT)
    assert Path(database_name).resolve() == TEST_HOME / "data" / "cardfactory.sqlite3"


def test_t1_core_paths_use_the_temporary_home():
    """RN-29 / CA-19 / T1: core.paths.app_home() inside the test process is the temporary home."""
    from core import paths

    assert Path(paths.app_home()).resolve() == TEST_HOME
    assert Path(paths.data_dir()).resolve() == TEST_HOME / "data"
