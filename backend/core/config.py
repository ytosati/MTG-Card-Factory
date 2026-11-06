"""Configuration read from `.env`: the only reader of the file and of the API keys.
Details: specs/plan.md, section 8.
"""

import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from core.environment import debug_enabled
from core.paths import app_home

DEFAULT_PORT = 47821
TEXT_PROVIDERS = ("openai", "anthropic", "google")
IMAGE_PROVIDERS = ("openai", "google")
SETTING_NAMES = (
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_MODEL",
    "IMAGE_PROVIDER",
    "IMAGE_API_KEY",
    "IMAGE_MODEL",
    "APP_PORT",
)

CODE_SETTING_TO_FIX = "config_invalid"
CODE_IGNORED = "ignored"


class Secret:
    """An API key whose text form is always `***`; only `reveal()` returns the value."""

    __slots__ = ("_value",)

    def __init__(self, value):
        self._value = value

    def reveal(self):
        """The key itself, for the provider factory only (see specs/plan.md, section 8)."""
        return self._value

    def __str__(self):
        return "***"

    def __repr__(self):
        return "Secret('***')"

    def __format__(self, format_spec):
        return "***"

    def __bool__(self):
        return bool(self._value)


@dataclass(frozen=True)
class SettingIssue:
    """A setting to fix or a notice: `{setting, code, message}` (specs/plan.md, section 6)."""

    setting: str
    code: str
    message: str


@dataclass(frozen=True)
class Config:
    """Configuration read from `.env`; the image key is the effective one after the fallback."""

    llm_provider: str
    llm_api_key: Secret
    llm_model: str
    image_provider: str
    image_api_key: Secret
    image_model: str
    app_port: int
    settings_to_fix: tuple = field(default=())
    notices: tuple = field(default=())
    # Kept only so the log filter can redact it (see spec RN-06); never used to call a provider.
    ignored_image_api_key: Secret = field(default=Secret(""), repr=False)


def default_path():
    """`.env` in the application home."""
    return app_home() / ".env"


def load_config(path=None):
    """Read `path` (default: `.env` in the application home) and check it; never raises."""
    values = _read_values(Path(path) if path is not None else default_path())
    return _build_config(values)


_cache = {}
_cache_lock = threading.Lock()


def get_config(path=None):
    """The configuration of `path`, read again only when the file's modification time changed."""
    file_path = Path(path) if path is not None else default_path()
    key = os.path.abspath(file_path)
    mtime = _modification_time(file_path)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        config = load_config(file_path)
        _cache[key] = (mtime, config)
        return config


def _modification_time(path):
    try:
        return os.stat(path).st_mtime_ns
    except OSError:
        return None


def _read_values(path):
    values = _parse(_read_text(path))
    # A global LLM_MODEL must never change a release; see spec RN-05.
    if debug_enabled():
        for name in SETTING_NAMES:
            override = _clean_value(os.environ.get(name, ""))
            if override:
                values[name] = override
    return values


def _read_text(path):
    try:
        # utf-8-sig drops the byte-order mark that Notepad may add.
        with open(path, encoding="utf-8-sig", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _parse(text):
    """`KEY=VALUE` lines as a dict; comments, blank and malformed lines are skipped."""
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        name, separator, value = stripped.partition("=")
        name = name.strip()
        if not separator or not name:
            continue
        values[name] = _clean_value(value)
    return values


def _clean_value(value):
    # No inline comments: an unquoted key may contain `#`.
    value = value.strip()
    if len(value) >= 2 and value[0] in "\"'" and value[-1] == value[0]:
        value = value[1:-1].strip()
    return value


def _parse_port(text):
    """The port written in `text`, the default when empty, or None when invalid (spec RN-47)."""
    if not text:
        return DEFAULT_PORT
    # isdigit() alone accepts non-ASCII digits such as full-width ones.
    if not (text.isascii() and text.isdigit()):
        return None
    # Very long digit strings would exceed int()'s digit limit and raise.
    significant = text.lstrip("0")
    if not significant or len(significant) > 5:
        return None
    port = int(significant)
    return port if port <= 65535 else None


def _setting_to_fix(setting, message):
    return SettingIssue(setting=setting, code=CODE_SETTING_TO_FIX, message=message)


def _notice(setting, message):
    return SettingIssue(setting=setting, code=CODE_IGNORED, message=message)


def _build_config(values):
    # Messages never quote a value: a key pasted into the wrong setting would leak.
    to_fix = []
    notices = []

    llm_provider = values.get("LLM_PROVIDER", "").lower()
    llm_key = values.get("LLM_API_KEY", "")
    llm_model = values.get("LLM_MODEL", "")
    if not llm_provider:
        to_fix.append(_setting_to_fix("LLM_PROVIDER", "Set LLM_PROVIDER to openai, anthropic or google."))
    elif llm_provider not in TEXT_PROVIDERS:
        to_fix.append(_setting_to_fix("LLM_PROVIDER", "LLM_PROVIDER is not a known provider. Use openai, anthropic or google."))
    if not llm_key:
        to_fix.append(_setting_to_fix("LLM_API_KEY", "Set LLM_API_KEY to the API key of the text provider."))
    if not llm_model:
        to_fix.append(_setting_to_fix("LLM_MODEL", "Set LLM_MODEL to the name of a text model of the provider."))

    image_provider = values.get("IMAGE_PROVIDER", "").lower()
    image_key = values.get("IMAGE_API_KEY", "")
    image_model = values.get("IMAGE_MODEL", "")
    ignored_image_key = ""
    # Empty image settings only make art unavailable; see spec RN-07 and RN-08.
    if image_provider:
        if image_provider in TEXT_PROVIDERS and image_provider not in IMAGE_PROVIDERS:
            to_fix.append(_setting_to_fix("IMAGE_PROVIDER", "IMAGE_PROVIDER cannot generate images. Use openai or google, or leave it empty."))
        elif image_provider not in IMAGE_PROVIDERS:
            to_fix.append(_setting_to_fix("IMAGE_PROVIDER", "IMAGE_PROVIDER is not a known image provider. Use openai or google, or leave it empty."))
        else:
            if not image_model:
                to_fix.append(_setting_to_fix("IMAGE_MODEL", "Set IMAGE_MODEL to the name of an image model of the image provider."))
            if not image_key:
                if image_provider == llm_provider:
                    image_key = llm_key
                else:
                    to_fix.append(_setting_to_fix("IMAGE_API_KEY", "Set IMAGE_API_KEY: the image provider differs from the text provider."))
    else:
        if image_key:
            notices.append(_notice("IMAGE_API_KEY", "IMAGE_API_KEY is ignored because IMAGE_PROVIDER is empty."))
            ignored_image_key = image_key
        if llm_provider in IMAGE_PROVIDERS:
            image_key = llm_key
        else:
            image_key = ""
            if image_model:
                notices.append(_notice("IMAGE_MODEL", "IMAGE_MODEL is ignored because IMAGE_PROVIDER is empty and the text provider cannot generate images."))
                image_model = ""

    app_port = _parse_port(values.get("APP_PORT", ""))
    if app_port is None:
        app_port = DEFAULT_PORT
        to_fix.append(_setting_to_fix("APP_PORT", f"APP_PORT must be a number from 1 to 65535. Using {DEFAULT_PORT}."))

    # An unrecognized provider is not kept: it may be a key pasted there (spec RN-06).
    if llm_provider not in TEXT_PROVIDERS:
        llm_provider = ""
    if image_provider not in IMAGE_PROVIDERS:
        image_provider = ""

    return Config(
        llm_provider=llm_provider,
        llm_api_key=Secret(llm_key),
        llm_model=llm_model,
        image_provider=image_provider,
        image_api_key=Secret(image_key),
        image_model=image_model,
        app_port=app_port,
        settings_to_fix=tuple(to_fix),
        notices=tuple(notices),
        ignored_image_api_key=Secret(ignored_image_key),
    )
