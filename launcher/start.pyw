"""Card Factory launcher, run with pythonw.exe (spec RN-27, RN-40).
Details: specs/plan.md, section 9.5 (launcher step 1, the bootstrap).
"""

import os
import sys

HOME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LAUNCHER_DIR = os.path.join(HOME, "launcher")
# The release zip keeps the backend under app/; a clone keeps it at the top.
_RELEASE_CODE_DIR = os.path.join(HOME, "app", "backend")
CODE_DIR = _RELEASE_CODE_DIR if os.path.isdir(_RELEASE_CODE_DIR) else os.path.join(HOME, "backend")

# The embeddable package ignores the script folder and PYTHONPATH.
for _folder in (LAUNCHER_DIR, CODE_DIR):
    if _folder not in sys.path:
        sys.path.insert(0, _folder)

os.environ["CARDFACTORY_HOME"] = HOME

# pythonw.exe has no standard streams; a write to None would fail.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import startup_checks  # noqa: E402


def main():
    """Run the startup sequence; `launch.main` begins with `startup_checks.run_checks`."""
    try:
        import launch
    except ModuleNotFoundError as error:
        if error.name not in ("launch", "core", "core.startup"):
            raise
        # Without a console, a missing code folder would otherwise end with no sign at all.
        startup_checks.message_box(
            f"Card Factory is missing some of its files:\n{CODE_DIR}",
            "Extract the whole release zip again into a new folder, then start Card Factory from there.",
        )
        return 1
    return launch.main(HOME, deps=launch.default_deps())


if __name__ == "__main__":
    sys.exit(main())
