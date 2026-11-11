"""The validators package imports no Django code (task T28, plan sections 3 and 5).

Validators are pure functions over a card and a lexicon. The package's
`apps.py` is the Django app registration and is the one module allowed to
import Django; every other module is enumerated, so validators added later
(T29, T138, Milestone 5) are covered without editing this file.
"""

import ast
import json
import subprocess
import sys

from tests.settings_probe import BACKEND_DIR, probe_environment

VALIDATORS_DIR = BACKEND_DIR / "validators"
# The Django app registration; Django loads it, the validators never import it.
APP_REGISTRATION = {"apps.py"}

IMPORT_PROBE = """
import importlib
import json
import pkgutil
import sys
sys.path.insert(0, sys.argv[1])
import validators
names = sorted(
    info.name
    for info in pkgutil.walk_packages(validators.__path__, "validators.")
    if info.name != "validators.apps" and ".migrations" not in info.name
)
for name in names:
    importlib.import_module(name)
result = validators.validate(
    {"name": "Bramblegate Wayfinder", "mana_cost": "{2}{G}", "mana_value": 4,
     "type_line": "Creature \\u2014 Elf Scout", "rules_text": "", "power": "2",
     "toughness": "2", "rarity": "common"},
    None,
    {"requested_color_identity": ["W", "U", "B", "R", "G"], "idea": "A forest scout."},
).to_dict()
print(json.dumps({
    "modules": names,
    "django_imported": any(m == "django" or m.startswith("django.") for m in sys.modules),
    "status": result["status"],
}))
"""


def _python_files():
    return [
        path
        for path in VALIDATORS_DIR.rglob("*.py")
        if path.name not in APP_REGISTRATION and "migrations" not in path.parts and "__pycache__" not in path.parts
    ]


def test_t28_validators_modules_never_import_django_statically():
    """RN-17 / T28 (plan section 3): no validators module except the app registration imports Django."""
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name == "django" or name.startswith("django."):
                    offenders.append(f"{path.name}: {name}")

    assert offenders == []


def test_t28_validators_package_has_a_mana_cost_module():
    """RN-17 / T28: the mana cost validator lives in the validators package."""
    names = {path.name for path in _python_files()}

    assert "mana_cost.py" in names


def test_t28_validate_runs_with_no_django_loaded(tmp_path):
    """RN-17 / T28 (plan section 5): importing every validators module and running `validate()` loads no Django code."""
    home = tmp_path / "home"
    home.mkdir()
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    completed = subprocess.run(
        [sys.executable, "-I", "-c", IMPORT_PROBE, str(BACKEND_DIR)],
        cwd=str(workdir),
        env=probe_environment({"DJANGO_SETTINGS_MODULE": None, "CARDFACTORY_HOME": str(home)}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    result = json.loads(lines[-1])

    assert "validators.mana_cost" in result["modules"]
    assert result["django_imported"] is False
    assert result["status"] == "rejected"
