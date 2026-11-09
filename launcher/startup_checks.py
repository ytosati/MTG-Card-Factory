"""Prerequisite checks the launcher runs before loading Django (spec RN-40, plan 9.5 step 2).

Only the standard library, with no network module: a failure here must be
shown even when nothing else of the application can load. `pathlib` is avoided
because it imports `urllib`.
"""

import ctypes
import os

WINDOW_TITLE = "Card Factory"
_MB_OK = 0x0
_MB_ICONERROR = 0x10
# pythonw has no window, so the box would otherwise open behind the Explorer.
_MB_SETFOREGROUND = 0x10000


def message_box(problem, fix):
    """Show a Windows message box naming the problem and the fix."""
    text = f"{problem}\n\n{fix}"
    ctypes.windll.user32.MessageBoxW(None, text, WINDOW_TITLE, _MB_OK | _MB_ICONERROR | _MB_SETFOREGROUND)


def run_checks(home, show_message):
    """Run the checks in order; show the first failure and return False, or return True."""
    home = os.fspath(home)
    for check in (_check_home_writable, _check_data_writable, _check_env_file):
        failure = check(home)
        if failure is not None:
            problem, fix = failure
            show_message(problem, fix)
            return False
    return True


def _is_writable(folder):
    """Create and delete a probe file, which is what the application will need to do."""
    probe = os.path.join(folder, f".write-check-{os.getpid()}.tmp")
    try:
        handle = os.open(probe, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    except OSError:
        return False
    os.close(handle)
    try:
        os.remove(probe)
    except OSError:
        pass
    return True


def _check_home_writable(home):
    if _is_writable(home):
        return None
    return (
        f"Card Factory cannot write to its folder:\n{home}",
        "Move the Card Factory folder to a place where you can create files, "
        "such as your Documents folder, and start it again from there.",
    )


def _check_data_writable(home):
    data = os.path.join(home, "data")
    if not os.path.isdir(data):
        try:
            os.mkdir(data)
        except OSError:
            pass
    if os.path.isdir(data) and _is_writable(data):
        return None
    return (
        f"Card Factory cannot write to its data folder:\n{data}",
        "Make sure the data folder is a folder you can write to (not read-only "
        "and not a file), or move the Card Factory folder to your Documents "
        "folder, and start it again.",
    )


def _check_env_file(home):
    env_file = os.path.join(home, ".env")
    if os.path.isfile(env_file):
        return None
    return (
        f"The configuration file .env is missing:\n{env_file}",
        "Extract the release zip again, or copy the .env file from it into the "
        "Card Factory folder, then start Card Factory again.",
    )
