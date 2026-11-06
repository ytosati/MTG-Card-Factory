"""Django secret key stored in `data/secret_key`, created on the first start.
Details: specs/plan.md, section 8.
"""

import secrets

from core.paths import data_dir

FILE_NAME = "secret_key"


def get_secret_key():
    """The key in `data/secret_key`; a new one is written when the file is missing or blank."""
    folder = data_dir()
    path = folder / FILE_NAME
    try:
        stored = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        stored = ""
    if stored:
        return stored
    folder.mkdir(parents=True, exist_ok=True)
    # 50 random bytes give about 67 characters, above Django's strength check (W009).
    key = secrets.token_urlsafe(50)
    path.write_text(key, encoding="utf-8")
    return key
