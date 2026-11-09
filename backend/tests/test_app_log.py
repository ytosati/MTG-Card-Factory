"""Application log file (task T87, spec RN-06, CA-06, plan sections 7 and 8).

Behaviour under test:
- After Django setup, the application logs to `<home>/data/logs/app.log`, with
  the home resolved by `core.paths`; the logs folder is created when missing.
- The file handler rotates by size (a non-zero `maxBytes` and `backupCount`).
- Every handler present in the logging system after setup carries
  `core.log_redaction.KeyRedactionFilter`, so a handler added later without it
  fails here.
- A key value of the configuration (8 characters or more) logged in a message,
  its arguments or an exception reaches the file as `***`, never as the value.
- The log format uses only the message, the standard record fields, the
  exception and the stack: an `extra` attribute never reaches the file.
- Every key value seen since the process started stays redacted after `.env`
  changes, kept in memory only.

Logging is configured when settings load, so the file tests run Django in a
fresh interpreter with a temporary home of their own (tests.settings_probe) and
inspect a logging system that pytest has not touched. pytest-django also
applies LOGGING in the test process, writing to the session's temporary home;
the in-process tests here use private loggers that do not propagate. The
interpreter exits before the temporary folder is removed, so no log file stays
open on Windows. Keys are fictional values that only look like keys.
"""

import json
import logging
import os
import re
import uuid
from pathlib import Path

import pytest

from tests.config_files import (
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    bump_mtime,
    clean_environment,  # noqa: F401 (fixture)
    env_text,
    full_text_settings,
    write_env,
    write_settings,
)
from tests.settings_probe import BACKEND_DIR, run_probe

IGNORED_IMAGE_KEY = "sk-fake-ignored-7777-IGNOREDKEY-not-real-6666"
MARKER = "***"

# Documented LogRecord attributes (Python logging, "LogRecord attributes").
STANDARD_RECORD_FIELDS = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)

# Runs in a fresh interpreter: Django setup, a description of every handler in
# the logging system, a few records through an application logger, then the
# content of app.log after every handler is closed.
LOG_PROBE = r"""
import json
import logging
import os

import django

# Created before setup, like a module-level logger imported early.
early_logger = logging.getLogger("t87early.module")

django.setup()

from core.log_redaction import KeyRedactionFilter

PARAMS = json.loads(__PARAMS__)


def describe(owner, handler):
    formatter = handler.formatter
    return {
        "logger": owner,
        "class": type(handler).__module__ + "." + type(handler).__qualname__,
        "redaction": any(isinstance(item, KeyRedactionFilter) for item in handler.filters),
        "filters": [type(item).__qualname__ for item in handler.filters],
        "base_filename": getattr(handler, "baseFilename", None),
        "max_bytes": getattr(handler, "maxBytes", None),
        "backup_count": getattr(handler, "backupCount", None),
        "formatter_class": None if formatter is None else type(formatter).__module__ + "." + type(formatter).__qualname__,
        "format": None if formatter is None else getattr(formatter, "_fmt", None),
    }


loggers = [("root", logging.getLogger())]
for name, item in sorted(logging.Logger.manager.loggerDict.items()):
    if isinstance(item, logging.Logger):
        loggers.append((name, item))
handlers = [describe(name, handler) for name, logger in loggers for handler in logger.handlers]

logger = logging.getLogger("api.exceptions")
text_key = PARAMS["text_key"]
image_key = PARAMS["image_key"]
ignored_key = PARAMS["ignored_key"]

logger.error("t87-args provider refused key %s at attempt %d", text_key, 2)
logger.error("t87-mapping header %(auth)s", {"auth": "Bearer " + image_key})
logger.error(f"t87-inline image key {image_key} end")
logger.error("t87-ignored %s end", ignored_key)
try:
    try:
        raise ConnectionError("t87-cause sent " + text_key)
    except ConnectionError as error:
        raise RuntimeError("t87-exception 401 invalid api key " + text_key) from error
except RuntimeError:
    logger.exception("t87-exception-message failed with %s", image_key)
logger.error("t87-stack marker", stack_info=True)
logger.error("t87-extra marker", extra={"detail": text_key, "card_text": "t87-extra-card-text " + ignored_key})
logging.getLogger("django.request").error("t87-django-request marker %s", text_key)
early_logger.error("t87-early-logger marker %s", text_key)

logging.shutdown()

log_path = os.path.join(PARAMS["home"], "data", "logs", "app.log")
content = None
if os.path.isfile(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as handle:
        content = handle.read()

print(json.dumps({"handlers": handlers, "log": content}))
"""


def _run_log_probe(home, workdir, debug=False):
    params = {
        "home": str(home),
        "text_key": FAKE_TEXT_KEY,
        "image_key": FAKE_IMAGE_KEY,
        "ignored_key": IGNORED_IMAGE_KEY,
    }
    code = LOG_PROBE.replace("__PARAMS__", repr(json.dumps(params)))
    overrides = {
        "PYTHONPATH": str(BACKEND_DIR),
        "DJANGO_SETTINGS_MODULE": "cardfactory.settings",
        "CARDFACTORY_HOME": str(home),
        "CARDFACTORY_DEBUG": "1" if debug else None,
    }
    return run_probe(code, overrides, cwd=workdir)


def _probe_home(root):
    """A home with a `.env` holding a text key, an image key and an ignored image key; no data/ yet."""
    home = root / "home"
    home.mkdir(parents=True)
    # Anthropic cannot generate images, so IMAGE_API_KEY without IMAGE_PROVIDER is ignored but kept for redaction.
    settings = full_text_settings(provider="anthropic")
    settings["IMAGE_API_KEY"] = IGNORED_IMAGE_KEY
    write_env(home, env_text(settings))
    return home


def _with_image_provider(home):
    """Rewrite `.env` so the image key is the effective one of a set image provider."""
    settings = {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_KEY": FAKE_TEXT_KEY,
        "LLM_MODEL": "fake-text-model-1",
        "IMAGE_PROVIDER": "openai",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    write_env(home, env_text(settings))


@pytest.fixture(scope="module")
def ignored_key_run(tmp_path_factory):
    """One probe run whose `.env` has a text key and an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER."""
    root = tmp_path_factory.mktemp("t87-ignored")
    home = _probe_home(root)
    workdir = root / "cwd"
    workdir.mkdir()
    result = _run_log_probe(home, workdir)
    return home, result


@pytest.fixture(scope="module")
def image_key_run(tmp_path_factory):
    """One probe run whose `.env` has a text key and the key of a set image provider."""
    root = tmp_path_factory.mktemp("t87-image")
    home = _probe_home(root)
    _with_image_provider(home)
    workdir = root / "cwd"
    workdir.mkdir()
    result = _run_log_probe(home, workdir)
    return home, result


def _expected_log_path(home):
    return Path(os.path.normcase(os.path.abspath(home / "data" / "logs" / "app.log")))


def _same_path(value, expected):
    return value is not None and Path(os.path.normcase(os.path.abspath(value))) == expected


def _app_log_handlers(home, result):
    expected = _expected_log_path(home)
    return [handler for handler in result["handlers"] if _same_path(handler["base_filename"], expected)]


def _log(result):
    content = result["log"]
    assert content is not None, "app.log was not written under <home>/data/logs/"
    return content


def _lines_with(content, marker):
    return [line for line in content.splitlines() if marker in line]


# Location and rotation


def test_t87_app_log_is_under_the_home_data_logs_folder(ignored_key_run):
    """T87 / plan section 7: the application log file is <home>/data/logs/app.log, with the home from CARDFACTORY_HOME."""
    home, result = ignored_key_run

    assert _app_log_handlers(home, result), (
        "No handler writes to <home>/data/logs/app.log. Handlers found: "
        f"{[(h['logger'], h['class'], h['base_filename']) for h in result['handlers']]}"
    )
    assert (home / "data" / "logs" / "app.log").is_file()


def test_t87_missing_logs_folder_is_created(ignored_key_run):
    """T87: a home with no data/ (and so no data/logs/) gets the logs folder on the first start."""
    home, result = ignored_key_run

    assert (home / "data" / "logs").is_dir()
    assert "t87-args" in _log(result)


def test_t87_file_handlers_write_only_under_the_home(ignored_key_run):
    """T87 / plan section 7: no handler writes a log file outside <home>/data/logs/."""
    home, result = ignored_key_run
    logs_dir = Path(os.path.normcase(os.path.abspath(home / "data" / "logs")))

    for handler in result["handlers"]:
        if handler["base_filename"] is None:
            continue
        path = Path(os.path.normcase(os.path.abspath(handler["base_filename"])))
        assert path.is_relative_to(logs_dir), f"{handler['class']} writes to {handler['base_filename']}"


def test_t87_app_log_rotates_by_size(ignored_key_run):
    """T87 / plan section 8: the app.log handler rotates by size, with a non-zero size limit and kept backups."""
    home, result = ignored_key_run
    handlers = _app_log_handlers(home, result)
    assert handlers, "No handler writes to <home>/data/logs/app.log."

    for handler in handlers:
        assert isinstance(handler["max_bytes"], int) and handler["max_bytes"] > 0, handler
        assert isinstance(handler["backup_count"], int) and handler["backup_count"] > 0, handler


# The redaction filter on every handler


@pytest.mark.parametrize("debug", [False, True], ids=["release", "debug"])
def test_rn06_t87_every_handler_carries_the_redaction_filter(tmp_path, debug):
    """RN-06 / CA-06 / T87: after setup, every handler in the logging system carries KeyRedactionFilter.

    Enumerates the live handlers of the root logger and every named logger, so
    a handler added later without the filter (including Django's own console
    handlers, active in debug) fails this test.
    """
    home = _probe_home(tmp_path)
    workdir = tmp_path / "cwd"
    workdir.mkdir()

    result = _run_log_probe(home, workdir, debug=debug)

    handlers = result["handlers"]
    assert _app_log_handlers(home, result), "No handler writes to <home>/data/logs/app.log."
    missing = [(h["logger"], h["class"], h["filters"]) for h in handlers if not h["redaction"]]
    assert not missing, f"Handlers without KeyRedactionFilter: {missing}"


# Keys in the file


def test_rn06_ca06_logged_exception_with_key_is_written_redacted(ignored_key_run):
    """RN-06 / CA-06 / T87 (Done when): an exception whose message and traceback hold the key reaches app.log as `***`."""
    _home, result = ignored_key_run
    content = _log(result)

    assert FAKE_TEXT_KEY not in content
    assert "t87-exception-message failed with" in content
    assert "RuntimeError: t87-exception 401 invalid api key ***" in content
    assert "ConnectionError: t87-cause sent ***" in content
    assert "Traceback (most recent call last):" in content


def test_rn06_ca06_key_in_message_args_is_written_redacted(ignored_key_run):
    """RN-06 / CA-06 / T87: a key passed as a %-format argument reaches app.log as `***`."""
    _home, result = ignored_key_run
    content = _log(result)

    lines = _lines_with(content, "t87-args")
    assert lines, "The record with arguments is missing from app.log."
    assert all(FAKE_TEXT_KEY not in line for line in lines)
    assert any("t87-args provider refused key *** at attempt 2" in line for line in lines)


def test_rn06_ca06_ignored_image_key_is_written_redacted(ignored_key_run):
    """RN-06 / CA-06 / T87: an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER never reaches app.log."""
    _home, result = ignored_key_run
    content = _log(result)

    assert IGNORED_IMAGE_KEY not in content
    assert any("t87-ignored *** end" in line for line in _lines_with(content, "t87-ignored"))


def test_rn06_ca06_image_key_in_message_and_mapping_is_written_redacted(image_key_run):
    """RN-06 / CA-06 / T87: the key of the image provider, inline or in a mapping argument, reaches app.log as `***`."""
    _home, result = image_key_run
    content = _log(result)

    assert FAKE_IMAGE_KEY not in content
    assert FAKE_TEXT_KEY not in content
    assert any("t87-inline image key *** end" in line for line in content.splitlines())
    assert any("t87-mapping header Bearer ***" in line for line in content.splitlines())
    assert "t87-exception-message failed with ***" in content


def test_rn06_ca06_key_in_stack_info_is_written_redacted(ignored_key_run):
    """RN-06 / CA-06 / T87: a record logged with its stack reaches app.log, and no key appears in it."""
    _home, result = ignored_key_run
    content = _log(result)

    assert "t87-stack marker" in content
    assert "Stack (most recent call last):" in content
    assert FAKE_TEXT_KEY not in content


def test_rn06_no_file_in_the_home_holds_a_key_except_the_env_file(ignored_key_run):
    """RN-06 / CA-06 / T87: after logging keys, no file of the home other than `.env` contains a key value."""
    home, _result = ignored_key_run
    keys = (FAKE_TEXT_KEY, IGNORED_IMAGE_KEY)
    env_file = home / ".env"

    for path in home.rglob("*"):
        if not path.is_file() or path == env_file:
            continue
        data = path.read_bytes()
        for key in keys:
            assert key.encode("utf-8") not in data, f"{path.relative_to(home)} holds a key value"


def test_t87_django_request_errors_reach_the_app_log(ignored_key_run):
    """T87 / plan section 8: an error logged by Django (`django.request`) reaches app.log, redacted."""
    _home, result = ignored_key_run
    content = _log(result)

    lines = _lines_with(content, "t87-django-request marker")
    assert lines, "A django.request error did not reach app.log."
    assert all(FAKE_TEXT_KEY not in line for line in lines)
    assert any(f"t87-django-request marker {MARKER}" in line for line in lines)


def test_t87_logger_created_before_setup_reaches_the_app_log(ignored_key_run):
    """T87: a logger created before Django setup is not disabled and still reaches app.log, redacted."""
    _home, result = ignored_key_run
    content = _log(result)

    lines = _lines_with(content, "t87-early-logger marker")
    assert lines, "A logger created before setup did not reach app.log."
    assert any(f"t87-early-logger marker {MARKER}" in line for line in lines)
    assert FAKE_TEXT_KEY not in content


# The log format: no extra fields


def test_rn06_t87_extra_attributes_never_reach_the_file(ignored_key_run):
    """RN-06 / CA-06 / T87 (decision): a record's `extra` values, which the filter does not cover, never reach app.log."""
    _home, result = ignored_key_run
    content = _log(result)

    assert "t87-extra marker" in content
    assert FAKE_TEXT_KEY not in content
    assert IGNORED_IMAGE_KEY not in content
    assert "t87-extra-card-text" not in content


def _format_fields(fmt):
    percent = re.findall(r"%\((\w+)\)", fmt)
    braces = re.findall(r"(?<!\{)\{(\w+)", fmt)
    dollars = re.findall(r"\$\{?(\w+)", fmt)
    return set(percent) | set(braces) | set(dollars)


def test_rn06_t87_log_format_uses_only_standard_record_fields(ignored_key_run):
    """RN-06 / T87 (decision): the app.log format names only standard LogRecord fields, never an extra one."""
    home, result = ignored_key_run
    handlers = _app_log_handlers(home, result)
    assert handlers, "No handler writes to <home>/data/logs/app.log."

    for handler in handlers:
        fmt = handler["format"]
        assert fmt, handler
        unknown = _format_fields(fmt) - STANDARD_RECORD_FIELDS
        assert not unknown, f"{handler['class']} on {handler['logger']} formats non-standard fields {unknown}: {fmt!r}"


def test_t87_app_log_has_a_format_with_the_message(ignored_key_run):
    """T87: the app.log handler has an explicit format that writes the message."""
    home, result = ignored_key_run
    handlers = _app_log_handlers(home, result)
    assert handlers, "No handler writes to <home>/data/logs/app.log."

    for handler in handlers:
        assert handler["format"], handler
        assert "message" in _format_fields(handler["format"]), handler["format"]


# Keys seen earlier in the process stay redacted (in-process, filter only)


class _CollectingHandler(logging.Handler):
    """Keeps every formatted line; a formatting error fails the test instead of printing."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []
        self.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))

    def emit(self, record):
        self.lines.append(self.format(record))

    def handleError(self, record):
        raise


@pytest.fixture
def home(clean_environment):  # noqa: F811 (fixture)
    return clean_environment


@pytest.fixture
def make_logger():
    """Private loggers, each with its own handler and its own KeyRedactionFilter instance."""
    from core.log_redaction import KeyRedactionFilter

    created = []

    def _make():
        handler = _CollectingHandler()
        handler.addFilter(KeyRedactionFilter())
        logger = logging.getLogger(f"cardfactory.test.t87.{uuid.uuid4().hex}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        logger.addHandler(handler)
        created.append((logger, handler))
        return logger, handler

    yield _make
    for logger, handler in created:
        logger.removeHandler(handler)
        handler.close()


def _unique_key(label):
    """A fictional key never used by another test, so memory from earlier tests cannot make a test pass."""
    return f"sk-fake-{label}-{uuid.uuid4().hex}-not-real"


def _text_and_image(text_key, image_key):
    return {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_KEY": text_key,
        "LLM_MODEL": "fake-text-model-1",
        "IMAGE_PROVIDER": "openai",
        "IMAGE_API_KEY": image_key,
        "IMAGE_MODEL": "fake-image-model-1",
    }


def test_rn06_t87_text_key_replaced_in_env_stays_redacted(home, make_logger):
    """RN-06 / CA-06 / T87 (decision): after LLM_API_KEY changes in .env, the old value is still redacted."""
    old_key = _unique_key("old-text")
    new_key = _unique_key("new-text")
    path = write_settings(home, full_text_settings(key=old_key))
    logger, handler = make_logger()
    logger.info("first call with %s", old_key)

    write_settings(home, full_text_settings(key=new_key))
    bump_mtime(path)
    logger.error("late error quoting old %s and new %s", old_key, new_key)

    output = "\n".join(handler.lines)
    assert old_key not in output
    assert new_key not in output
    assert handler.lines[-1] == f"ERROR|late error quoting old {MARKER} and new {MARKER}"


def test_rn06_t87_image_key_replaced_in_env_stays_redacted(home, make_logger):
    """RN-06 / CA-06 / T87 (decision): after IMAGE_API_KEY changes in .env, the old image key is still redacted."""
    text_key = _unique_key("text")
    old_image = _unique_key("old-image")
    new_image = _unique_key("new-image")
    path = write_settings(home, _text_and_image(text_key, old_image))
    logger, handler = make_logger()
    logger.info("art call ready")

    write_settings(home, _text_and_image(text_key, new_image))
    bump_mtime(path)
    logger.error("art failed: old %s new %s", old_image, new_image)

    assert handler.lines[-1] == f"ERROR|art failed: old {MARKER} new {MARKER}"


def test_rn06_t87_ignored_image_key_replaced_in_env_stays_redacted(home, make_logger):
    """RN-06 / T87 (decision): an ignored IMAGE_API_KEY removed from .env stays redacted."""
    text_key = _unique_key("text")
    ignored_key = _unique_key("ignored")
    settings = full_text_settings(provider="anthropic", key=text_key)
    settings["IMAGE_API_KEY"] = ignored_key
    path = write_settings(home, settings)
    logger, handler = make_logger()
    logger.info("status read")

    write_settings(home, full_text_settings(provider="anthropic", key=text_key))
    bump_mtime(path)
    logger.warning("leftover %s", ignored_key)

    assert handler.lines[-1] == f"WARNING|leftover {MARKER}"


def test_rn06_t87_key_stays_redacted_after_env_file_is_removed(home, make_logger):
    """RN-06 / T87 (decision): with `.env` deleted (no key configured now), a key seen earlier is still redacted."""
    old_key = _unique_key("removed")
    path = write_settings(home, full_text_settings(key=old_key))
    from core.config import get_config

    get_config()  # the key is read, as a provider call would, but never logged
    logger, handler = make_logger()

    path.unlink()
    logger.error("after removal %s", old_key)

    assert handler.lines[-1] == f"ERROR|after removal {MARKER}"


def test_rn06_t87_key_stays_redacted_in_exception_after_change(home, make_logger):
    """RN-06 / CA-06 / T87 (decision): a replaced key inside a later traceback is redacted."""
    old_key = _unique_key("old-exc")
    new_key = _unique_key("new-exc")
    path = write_settings(home, full_text_settings(key=old_key))
    from core.config import get_config

    get_config()  # the key is read, as a provider call would, but never logged
    logger, handler = make_logger()

    write_settings(home, full_text_settings(key=new_key))
    bump_mtime(path)
    try:
        raise RuntimeError(f"401 for {old_key}")
    except RuntimeError:
        logger.exception("stale call failed")

    output = "\n".join(handler.lines)
    assert old_key not in output
    assert f"RuntimeError: 401 for {MARKER}" in output


def test_rn06_t87_seen_keys_are_shared_by_every_filter_in_the_process(home, make_logger):
    """RN-06 / T87 (decision): a key seen by one handler's filter is redacted by another handler's filter after it changes.

    Each configured handler has its own filter instance, so the memory is per
    process, not per filter.
    """
    old_key = _unique_key("shared-old")
    new_key = _unique_key("shared-new")
    path = write_settings(home, full_text_settings(key=old_key))
    first_logger, _first_handler = make_logger()
    first_logger.info("seen here")

    write_settings(home, full_text_settings(key=new_key))
    bump_mtime(path)
    second_logger, second_handler = make_logger()
    second_logger.error("other handler %s", old_key)

    assert second_handler.lines == [f"ERROR|other handler {MARKER}"]


def test_rn06_t87_seen_keys_are_kept_in_memory_only(home, make_logger):
    """RN-06 / T87 (decision): remembering replaced keys writes no file; the home holds only `.env`."""
    old_key = _unique_key("memory-old")
    new_key = _unique_key("memory-new")
    path = write_settings(home, full_text_settings(key=old_key))
    logger, handler = make_logger()
    logger.info("configured")
    write_settings(home, full_text_settings(key=new_key))
    bump_mtime(path)
    logger.info("old %s new %s", old_key, new_key)

    assert handler.lines[-1] == f"INFO|old {MARKER} new {MARKER}"
    assert sorted(item.name for item in home.rglob("*")) == [".env"]


# Keys read by the configuration but never logged before the change (plan section 8:
# "a call made with a key replaced in .env cannot log the old value")


def _settings_with_text_key(key):
    return full_text_settings(key=key)


def _settings_with_image_key(key):
    return _text_and_image("sk-fake-text-fixed-0000-TEXT-not-real", key)


def _settings_with_ignored_key(key):
    settings = full_text_settings(provider="anthropic", key="sk-fake-text-fixed-1111-TEXT-not-real")
    settings["IMAGE_API_KEY"] = key
    return settings


@pytest.mark.parametrize(
    "build_settings",
    [_settings_with_text_key, _settings_with_image_key, _settings_with_ignored_key],
    ids=["text-key", "image-key", "ignored-image-key"],
)
def test_rn06_t87_key_only_read_by_config_stays_redacted_after_change(home, make_logger, build_settings):
    """RN-06 / CA-06 / T87 (decision): a key only read through get_config(), never logged, stays redacted after .env changes.

    A provider call reads the configuration, the person replaces the key in
    `.env`, and the call then fails and logs the old value: it must not appear.
    """
    from core.config import get_config

    old_key = _unique_key("read-old")
    new_key = _unique_key("read-new")
    path = write_settings(home, build_settings(old_key))
    config = get_config()
    assert old_key in {
        config.llm_api_key.reveal(),
        config.image_api_key.reveal(),
        config.ignored_image_api_key.reveal(),
    }  # the fictional key is really part of the configuration that was read

    write_settings(home, build_settings(new_key))
    bump_mtime(path)
    logger, handler = make_logger()
    logger.error("stale call failed with %s", old_key)
    logger.error(f"inline {old_key} end")

    output = "\n".join(handler.lines)
    assert old_key not in output
    assert handler.lines == [f"ERROR|stale call failed with {MARKER}", f"ERROR|inline {MARKER} end"]


def test_rn06_t87_key_only_read_by_config_stays_redacted_in_traceback(home, make_logger):
    """RN-06 / CA-06 / T87 (decision): a key read but never logged, then replaced, is redacted inside a traceback."""
    from core.config import get_config

    old_key = _unique_key("read-exc-old")
    path = write_settings(home, full_text_settings(key=old_key))
    get_config()

    write_settings(home, full_text_settings(key=_unique_key("read-exc-new")))
    bump_mtime(path)
    logger, handler = make_logger()
    try:
        raise RuntimeError(f"401 Unauthorized for {old_key}")
    except RuntimeError:
        logger.exception("provider call failed")

    output = "\n".join(handler.lines)
    assert old_key not in output
    assert f"RuntimeError: 401 Unauthorized for {MARKER}" in output


# AppLogHandler: rotation and a file closed between records


@pytest.fixture
def app_log_handler(tmp_path):
    """An AppLogHandler on a temporary file with a tiny size limit; closed in teardown."""
    from core.app_log import AppLogHandler

    path = tmp_path / "logs" / "app.log"
    path.parent.mkdir()
    handler = AppLogHandler(str(path), maxBytes=200, backupCount=2, encoding="utf-8", delay=True)
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    yield handler, path
    handler.close()


def _record(message):
    return logging.LogRecord("t87.rotation", logging.INFO, __file__, 1, message, None, None)


def test_t87_app_log_handler_rotates_when_the_size_limit_is_reached(app_log_handler):
    """T87 / plan section 8: past maxBytes the file rotates to app.log.1, keeping at most backupCount backups."""
    handler, path = app_log_handler

    for index in range(20):
        handler.handle(_record(f"rotation line {index:02d} " + "x" * 60))

    assert path.is_file()
    assert path.with_name("app.log.1").is_file()
    assert path.with_name("app.log.2").is_file()
    assert not path.with_name("app.log.3").exists()
    assert path.stat().st_size <= 200
    assert "rotation line 19" in path.read_text(encoding="utf-8")


def test_t87_app_log_handler_closes_the_file_after_each_record(app_log_handler):
    """T87: the file is closed between records, so on Windows it can be renamed or deleted right after one."""
    handler, path = app_log_handler

    handler.handle(_record("first record"))

    assert handler.stream is None
    moved = path.with_name("moved.log")
    os.replace(path, moved)
    moved.unlink()

    handler.handle(_record("second record"))

    assert handler.stream is None
    assert path.read_text(encoding="utf-8").strip() == "INFO second record"
    path.unlink()
