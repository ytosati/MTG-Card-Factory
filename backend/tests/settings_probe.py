"""Test helper: evaluates the Django settings in a fresh Python process.

Settings are read at import time, so each probe runs in a subprocess with a
controlled environment instead of reloading modules inside the test process.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.project_environment import is_project_variable

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_DIR.parent

# Interpreter variables that could change what a probe imports.
_PYTHON_VARIABLES = {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}


def probe_environment(overrides):
    """Return a copy of the current environment without project settings, plus overrides.

    An override set to None removes the variable.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if not is_project_variable(name) and name.upper() not in _PYTHON_VARIABLES
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def run_probe(code, env_overrides, cwd):
    """Run `code` in a new interpreter and return the JSON object it prints last."""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(cwd),
        env=probe_environment(env_overrides),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "Settings probe failed with exit code "
            f"{completed.returncode}.\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    assert lines, f"Settings probe printed nothing.\nstderr:\n{completed.stderr}"
    return json.loads(lines[-1])
