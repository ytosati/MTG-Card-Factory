"""Card Factory launcher, run with pythonw.exe (spec RN-27, RN-40; plan section 9.5)."""

import os
import sys

HOME = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
LAUNCHER_DIR = os.path.join(HOME, "launcher")

if LAUNCHER_DIR not in sys.path:
    sys.path.insert(0, LAUNCHER_DIR)

import startup_checks  # noqa: E402


def main():
    if not startup_checks.run_checks(HOME, startup_checks.message_box):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
