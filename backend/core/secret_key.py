"""Django secret key stored in `data/secret_key`, created on the first start.
Details: specs/plan.md, section 8.
"""

import secrets

from core.paths import data_dir
from core.startup import StartupError

FILE_NAME = "secret_key"


def get_secret_key():
    """The key in `data/secret_key`; a new one is written when the file is missing, blank or not UTF-8."""
    folder = data_dir()
    path = folder / FILE_NAME
    try:
        content = path.read_bytes()
    except FileNotFoundError:
        content = b""
    except OSError as error:
        # Includes a folder at the path; an unreadable file is never overwritten.
        raise _unusable_file() from error
    try:
        stored = content.decode("utf-8").strip()
    except UnicodeDecodeError:
        stored = ""
    if stored:
        return stored
    # 50 random bytes give about 67 characters, above Django's strength check (W009).
    key = secrets.token_urlsafe(50)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path.write_text(key, encoding="utf-8")
    except OSError as error:
        raise _unusable_file() from error
    return key


def _unusable_file():
    # Never quotes the content: it is the key.
    return StartupError(
        "The file data/secret_key cannot be read or written.",
        "Check its permissions, or delete it so Card Factory creates a new one.",
    )
