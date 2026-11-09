"""Configuration read from `.env`: the only reader of the file and of the API keys.
Details: specs/plan.md, section 8.
"""

import codecs
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
# The setting of the item for a file that cannot be read (specs/plan.md, section 6).
ENV_FILE_SETTING = ".env"
# Messages never quote the file: it holds the keys.
CANNOT_OPEN_MESSAGE = "The .env file cannot be opened. Check its permissions and that it is a file, not a folder."
NOT_TEXT_MESSAGE = "The .env file cannot be read as text. Save it as UTF-8."
CODE_IGNORED = "ignored"
# How provider keys start (OpenAI and Anthropic, Google); case-sensitive, as the keys are.
KEY_PREFIXES = ("sk-", "AIza")


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
    # The file exists but could not be read; nothing else about it is reported (spec CA-77).
    unreadable: bool = False


def default_path():
    """`.env` in the application home."""
    return app_home() / ".env"


def load_config(path=None):
    """Read `path` (default: `.env` in the application home) and check it; never raises."""
    text, problem = _read_text(Path(path) if path is not None else default_path())
    config = _unreadable_config(problem) if problem else _build_config(_with_overrides(_parse(text)))
    _remember_keys(config)
    return config


def _remember_keys(config):
    """Let the log filter keep redacting these keys after `.env` changes (spec RN-06)."""
    # Local import: core.log_redaction imports this module.
    from core.log_redaction import remember_keys

    remember_keys(config)


_cache = {}
_cache_lock = threading.Lock()


def get_config(path=None):
    """The configuration of `path`, read again only when the file's modification time or size changed."""
    file_path = Path(path) if path is not None else default_path()
    key = os.path.abspath(file_path)
    stamp = _file_stamp(file_path)
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and cached[0] == stamp:
            # Every read remembers the keys, a cached one as well as a fresh one.
            _remember_keys(cached[1])
            return cached[1]
        config = load_config(file_path)
        # A failed read is tried again on the next call: a fixed permission leaves the stamp unchanged.
        if not config.unreadable:
            _cache[key] = (stamp, config)
        return config


def _file_stamp(path):
    """Modification time and size; the size catches a save within the timestamp precision."""
    try:
        status = os.stat(path)
        return (status.st_mtime_ns, status.st_size)
    except OSError:
        return None


def _with_overrides(values):
    """`values` with the process variables applied in debug mode only."""
    # A global LLM_MODEL must never change a release; see spec RN-05.
    if debug_enabled():
        for name in SETTING_NAMES:
            override = _clean_value(os.environ.get(name, ""))
            if override:
                values[name] = override
    return values


def _read_text(path):
    """The file's text and the message of its problem, or None; a missing file is empty text (spec RN-40)."""
    try:
        with open(path, "rb") as handle:
            content = handle.read()
    except FileNotFoundError:
        return "", None
    except OSError:
        # Includes a folder at the path.
        return "", CANNOT_OPEN_MESSAGE
    if content.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        # Notepad "Unicode"; the utf-16 codec reads the byte-order mark and drops it.
        text = content.decode("utf-16", errors="replace")
    else:
        # utf-8-sig drops the byte-order mark that Notepad may add; a stray byte keeps the other lines.
        text = content.decode("utf-8-sig", errors="replace")
    # NUL characters mean another encoding, such as UTF-16 with no byte-order mark.
    if "\x00" in text:
        return "", NOT_TEXT_MESSAGE
    return text, None


def _unreadable_config(message):
    """An empty configuration with the single `.env` item: no other setting and no port change (spec CA-77)."""
    return Config(
        llm_provider="",
        llm_api_key=Secret(""),
        llm_model="",
        image_provider="",
        image_api_key=Secret(""),
        image_model="",
        app_port=DEFAULT_PORT,
        settings_to_fix=(_setting_to_fix(ENV_FILE_SETTING, message),),
        unreadable=True,
    )


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


def _looks_like_key(value, keys):
    """Whether a model value is a configured key or starts like one (spec CA-78)."""
    return value in keys or value.startswith(KEY_PREFIXES)


def _build_config(values):
    # Messages never quote a value: a key pasted into the wrong setting would leak.
    to_fix = []
    notices = []
    # Every key value written in the file, used or not, including an ignored image key.
    keys = {key for key in (values.get("LLM_API_KEY", ""), values.get("IMAGE_API_KEY", "")) if key}

    llm_provider = values.get("LLM_PROVIDER", "").lower()
    llm_key = values.get("LLM_API_KEY", "")
    llm_model = values.get("LLM_MODEL", "")
    if not llm_provider:
        to_fix.append(_setting_to_fix("LLM_PROVIDER", "Set LLM_PROVIDER to openai, anthropic or google."))
    elif llm_provider not in TEXT_PROVIDERS:
        to_fix.append(_setting_to_fix("LLM_PROVIDER", "LLM_PROVIDER is not a known provider. Use openai, anthropic or google."))
    if not llm_key:
        to_fix.append(_setting_to_fix("LLM_API_KEY", "Set LLM_API_KEY to the API key of the text provider."))
    # A key-like model is not kept, like an unknown provider value (spec RN-06).
    if llm_model and _looks_like_key(llm_model, keys):
        llm_model = ""
        to_fix.append(_setting_to_fix("LLM_MODEL", "LLM_MODEL looks like an API key. Set it to the name of a text model of the provider."))
    elif not llm_model:
        to_fix.append(_setting_to_fix("LLM_MODEL", "Set LLM_MODEL to the name of a text model of the provider."))

    image_provider = values.get("IMAGE_PROVIDER", "").lower()
    image_key = values.get("IMAGE_API_KEY", "")
    image_model = values.get("IMAGE_MODEL", "")
    ignored_image_key = ""
    # Reported once, even where an empty or ignored image model would be reported too.
    image_model_looks_like_key = bool(image_model) and _looks_like_key(image_model, keys)
    if image_model_looks_like_key:
        image_model = ""
        to_fix.append(_setting_to_fix("IMAGE_MODEL", "IMAGE_MODEL looks like an API key. Set it to the name of an image model, or leave it empty."))
    # Empty image settings only make art unavailable; see spec RN-07 and RN-08.
    if image_provider:
        if image_provider in TEXT_PROVIDERS and image_provider not in IMAGE_PROVIDERS:
            to_fix.append(_setting_to_fix("IMAGE_PROVIDER", "IMAGE_PROVIDER cannot generate images. Use openai or google, or leave it empty."))
        elif image_provider not in IMAGE_PROVIDERS:
            to_fix.append(_setting_to_fix("IMAGE_PROVIDER", "IMAGE_PROVIDER is not a known image provider. Use openai or google, or leave it empty."))
        else:
            if not image_model and not image_model_looks_like_key:
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
