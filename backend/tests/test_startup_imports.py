"""Modules the launcher imports before the Django settings load (task T7, spec RN-40, plan section 9.5).

The launcher imports only `core.config` and `core.startup`; it loads the
Django settings later, inside its `StartupError` handling (launcher step 4).
Each probe runs in an isolated interpreter (`-I`: no PYTHONPATH, no user site,
no script folder on the path) with DJANGO_SETTINGS_MODULE unset.
"""

import json
import subprocess
import sys

from tests.settings_probe import BACKEND_DIR, probe_environment

CONFIG_PROBE = """
import json
import sys
sys.path.insert(0, sys.argv[1])
import core.config
config = core.config.load_config()
print(json.dumps({
    "django_imported": "django" in sys.modules,
    "app_port": config.app_port,
}))
"""

STARTUP_PROBE = """
import json
import sys
sys.path.insert(0, sys.argv[1])
import core.startup
error = core.startup.StartupError("fictional problem", "fictional fix")
configured = None
if "django.conf" in sys.modules:
    configured = sys.modules["django.conf"].settings.configured
print(json.dumps({
    "problem": error.problem,
    "fix": error.fix,
    "has_serve": callable(getattr(core.startup, "serve", None)),
    "settings_configured": configured,
}))
"""


def _run_isolated(code, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code, str(BACKEND_DIR)],
        cwd=str(workdir),
        env=probe_environment({"DJANGO_SETTINGS_MODULE": None, "CARDFACTORY_HOME": str(home)}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, completed.stderr
    return json.loads(lines[-1]), home


def test_t7_rn40_core_config_imports_with_no_django_settings(tmp_path):
    """RN-40 / T7 (plan 9.5): core.config imports and reads the configuration with no Django settings and no Django."""
    result, home = _run_isolated(CONFIG_PROBE, tmp_path)

    assert result["django_imported"] is False
    assert result["app_port"] == 47821
    assert not (home / "data").exists()


def test_t7_rn40_core_startup_imports_with_no_django_settings(tmp_path):
    """RN-40 / T7 (plan 9.5, step 4): core.startup imports before the settings load, so the launcher can catch StartupError."""
    result, home = _run_isolated(STARTUP_PROBE, tmp_path)

    assert result["problem"] == "fictional problem"
    assert result["fix"] == "fictional fix"
    assert result["has_serve"] is True
    assert result["settings_configured"] in (None, False)
    assert not (home / "data").exists()
