"""Key redaction in log records (task T5, spec RN-06, CA-06, plan section 8).

API under test: `core.log_redaction.KeyRedactionFilter`, a `logging.Filter`
built with no arguments (usable from a dictConfig `"()"` entry). On each record
it reads the current configuration with `core.config.get_config()` and replaces
with `***` every key the configuration holds (the text key, the effective image
key and an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER) in the message,
its formatted arguments, the exception text and the stack info, including a
record whose arguments do not match its message. It never drops a record. Keys
shorter than 8 characters are left alone.

Every test uses a temporary `.env` in a cleared environment, never the
repository `.env`. Log files, handlers and rotation belong to a later task.
"""

import logging
import uuid

import pytest

from tests.config_files import (
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    bump_mtime,
    clean_environment,  # noqa: F401 (fixture)
    full_text_settings,
    write_settings,
)

FORMAT = "%(levelname)s|%(message)s"


class _CollectingHandler(logging.Handler):
    """Keeps every formatted line; a formatting error fails the test instead of printing."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []
        self.setFormatter(logging.Formatter(FORMAT))

    def emit(self, record):
        self.lines.append(self.format(record))

    def handleError(self, record):
        raise


@pytest.fixture
def home(clean_environment):  # noqa: F811 (fixture)
    return clean_environment


@pytest.fixture
def redacted_logger():
    """A private logger whose only handler carries the redaction filter."""
    from core.log_redaction import KeyRedactionFilter

    handler = _CollectingHandler()
    handler.addFilter(KeyRedactionFilter())
    logger = logging.getLogger(f"cardfactory.test.t5.{uuid.uuid4().hex}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(handler)
    yield logger, handler
    logger.removeHandler(handler)


def _output(handler):
    return "\n".join(handler.lines)


def _text_and_image(text_key=FAKE_TEXT_KEY, image_key=FAKE_IMAGE_KEY):
    return {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_KEY": text_key,
        "LLM_MODEL": "fake-text-model-1",
        "IMAGE_PROVIDER": "openai",
        "IMAGE_API_KEY": image_key,
        "IMAGE_MODEL": "fake-image-model-1",
    }


# Where the key appears


def test_rn06_ca06_key_in_message_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: a key written into the message itself never reaches the log line."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    logger.warning(f"provider rejected key {FAKE_TEXT_KEY} for model fake-text-model-1")

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "provider rejected key" in output
    assert "for model fake-text-model-1" in output
    assert len(handler.lines) == 1


def test_rn06_ca06_key_in_formatted_args_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: a key passed as a %-format argument is redacted after formatting."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    logger.info("calling %s with key %s (attempt %d)", "openai", FAKE_TEXT_KEY, 2)

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "calling openai with key" in output
    assert "(attempt 2)" in output


def test_rn06_ca06_key_in_mapping_args_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: a key passed through a mapping argument is redacted."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    logger.info("headers: %(auth)s", {"auth": f"Bearer {FAKE_TEXT_KEY}"})

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "headers: Bearer" in output


def test_rn06_ca06_key_in_non_string_message_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: a message that is an object (here an exception) is redacted too."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    logger.error(ValueError(f"bad key {FAKE_TEXT_KEY}"))

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "bad key" in output


def test_rn06_ca06_key_in_exception_text_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: when a provider error carries the key, the logged traceback does not."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    try:
        raise RuntimeError(f"401 Unauthorized: invalid api key {FAKE_TEXT_KEY}")
    except RuntimeError:
        logger.exception("text generation failed")

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "text generation failed" in output
    assert "RuntimeError" in output
    assert "401 Unauthorized: invalid api key" in output


def test_rn06_ca06_key_in_chained_exception_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: the key is redacted in every part of a chained traceback."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    try:
        try:
            raise ConnectionError(f"sent {FAKE_TEXT_KEY}")
        except ConnectionError as error:
            raise RuntimeError(f"wrapped {FAKE_TEXT_KEY}") from error
    except RuntimeError:
        logger.exception("call failed")

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "ConnectionError" in output
    assert "RuntimeError" in output


def test_rn06_key_repeated_in_one_record_is_fully_redacted(home, redacted_logger):
    """RN-06 / T5: every occurrence of the key in a record is redacted."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    logger.info("%s %s", FAKE_TEXT_KEY, f"{FAKE_TEXT_KEY}{FAKE_TEXT_KEY}")

    assert FAKE_TEXT_KEY not in _output(handler)


def test_rn06_key_inside_a_huge_message_is_redacted(home, redacted_logger):
    """RN-06 / T5: a key in the middle of a very long message is still redacted."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger
    padding = "x" * 500_000

    logger.info(f"{padding}{FAKE_TEXT_KEY}{padding}")

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert output.startswith(f"INFO|{padding}")
    assert output.endswith(padding)


# Which keys


def test_rn06_ca06_text_and_image_keys_are_both_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: the configured text key and image key are both redacted in one record."""
    write_settings(home, _text_and_image())
    logger, handler = redacted_logger

    logger.info("text=%s image=%s", FAKE_TEXT_KEY, FAKE_IMAGE_KEY)

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert FAKE_IMAGE_KEY not in output
    assert "text=" in output
    assert "image=" in output


def test_rn06_ca06_image_key_alone_is_redacted(home, redacted_logger):
    """RN-06 / CA-06 / T5: a record with only the image key is redacted."""
    write_settings(home, _text_and_image())
    logger, handler = redacted_logger

    logger.error("image provider refused %s", FAKE_IMAGE_KEY)

    output = _output(handler)
    assert FAKE_IMAGE_KEY not in output
    assert "image provider refused" in output


@pytest.mark.parametrize(
    "settings",
    [
        # IMAGE_API_KEY empty and the image provider equals the text provider (RN-05).
        {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": FAKE_TEXT_KEY,
            "LLM_MODEL": "fake-text-model-1",
            "IMAGE_PROVIDER": "openai",
            "IMAGE_API_KEY": "",
            "IMAGE_MODEL": "fake-image-model-1",
        },
        # No image provider; an image-capable text provider is used for art (RN-07).
        {
            "LLM_PROVIDER": "google",
            "LLM_API_KEY": FAKE_TEXT_KEY,
            "LLM_MODEL": "fake-text-model-1",
        },
    ],
    ids=["same-image-provider", "text-provider-for-art"],
)
def test_rn06_effective_image_key_equal_to_text_key_is_redacted(home, redacted_logger, settings):
    """RN-06 / CA-06 / T5: when the effective image key is the text key, it is redacted once and fully."""
    write_settings(home, settings)
    logger, handler = redacted_logger

    logger.warning("art call used %s", FAKE_TEXT_KEY)

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "art call used" in output


def test_rn06_image_key_containing_text_key_leaves_neither(home, redacted_logger):
    """RN-06 / T5: one key containing the other does not let either survive the redaction."""
    image_key = f"{FAKE_TEXT_KEY}-EXTENDED-0000"
    write_settings(home, _text_and_image(image_key=image_key))
    logger, handler = redacted_logger

    logger.info("keys %s and %s", image_key, FAKE_TEXT_KEY)

    output = _output(handler)
    assert image_key not in output
    assert FAKE_TEXT_KEY not in output


@pytest.mark.parametrize(
    "key",
    [
        "sk-fake.*+?[](){}|\\$^-0000",
        "sk-fake-%s%d%(name)s-1111",
        "sk-fake#hash;semi'quote-2222",
        "sk-fake-çãõ-ключ-密钥-3333",
    ],
    ids=["regex-characters", "percent-format", "hash-and-quotes", "non-ascii"],
)
def test_rn06_keys_with_odd_characters_are_redacted_literally(home, redacted_logger, key):
    """RN-06 / T5: keys are matched as literal text; odd characters neither break logging nor leak."""
    write_settings(home, full_text_settings(key=key))
    from core.config import get_config

    assert get_config().llm_api_key.reveal() == key  # the fictional key is read back intact
    logger, handler = redacted_logger

    logger.info("key %s here", key)
    logger.info(f"inline {key} here")

    output = _output(handler)
    assert key not in output
    assert "key " in output
    assert "inline " in output
    assert len(handler.lines) == 2


def test_rn06_ca06_key_fixed_in_file_is_redacted_without_restart(home, redacted_logger):
    """RN-06 / CA-73 / T5: after the key in .env changes, the same filter redacts the new key."""
    path = write_settings(home, full_text_settings())
    logger, handler = redacted_logger
    logger.info("first %s", FAKE_TEXT_KEY)

    new_key = "sk-fake-text-9999-NEWKEY-not-real-8888"
    write_settings(home, full_text_settings(key=new_key))
    bump_mtime(path)
    logger.info("second %s", new_key)

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert new_key not in output
    assert "first" in output
    assert "second" in output


# Records that must not change


def test_t5_record_without_keys_is_unchanged(home, redacted_logger):
    """T5: a record with no key is written exactly as without the filter."""
    write_settings(home, _text_and_image())
    logger, handler = redacted_logger

    logger.info("build finished: %d cards, %s", 42, "ok")

    assert handler.lines == ["INFO|build finished: 42 cards, ok"]


def test_t5_filter_never_drops_a_record(home):
    """T5: the filter redacts but always lets the record through."""
    from core.log_redaction import KeyRedactionFilter

    write_settings(home, full_text_settings())
    record = logging.LogRecord("t5", logging.ERROR, __file__, 1, "key %s", (FAKE_TEXT_KEY,), None)

    assert KeyRedactionFilter().filter(record)
    assert FAKE_TEXT_KEY not in record.getMessage()


@pytest.mark.parametrize("short_key", ["a", "abc", "abc1234"], ids=["1-char", "3-chars", "7-chars"])
def test_t5_short_key_changes_nothing(home, redacted_logger, short_key):
    """T5 (Done when): a configured key under 8 characters changes nothing in a record."""
    write_settings(home, full_text_settings(key=short_key))
    logger, handler = redacted_logger

    logger.info("value %s and abc1234 and a cat", short_key)
    logger.info("plain abc1234 abcabc")

    assert handler.lines == [
        f"INFO|value {short_key} and abc1234 and a cat",
        "INFO|plain abc1234 abcabc",
    ]


def test_t5_empty_key_changes_nothing(home, redacted_logger):
    """T5 (Done when): an empty configured key changes nothing in a record."""
    write_settings(home, full_text_settings(key=""))
    logger, handler = redacted_logger

    logger.info("empty %s key, text stays: %s", "", "abc 123")

    assert handler.lines == ["INFO|empty  key, text stays: abc 123"]


def test_t5_eight_character_key_is_redacted(home, redacted_logger):
    """T5: the length limit is "under 8"; a key of exactly 8 characters is redacted."""
    key = "k8-fake1"
    assert len(key) == 8
    write_settings(home, full_text_settings(key=key))
    logger, handler = redacted_logger

    logger.info("token %s end", key)

    output = _output(handler)
    assert key not in output
    assert "token" in output
    assert "end" in output


def test_t5_short_text_key_does_not_stop_image_key_redaction(home, redacted_logger):
    """T5: a short text key is ignored while a long image key is still redacted."""
    write_settings(home, _text_and_image(text_key="abc1234"))
    logger, handler = redacted_logger

    logger.info("text %s image %s", "abc1234", FAKE_IMAGE_KEY)

    output = _output(handler)
    assert FAKE_IMAGE_KEY not in output
    assert "text abc1234 image" in output


def test_t5_missing_env_file_changes_nothing(home, redacted_logger):
    """T5: with no .env (no key configured) records pass through unchanged and logging does not fail."""
    assert not (home / ".env").exists()
    logger, handler = redacted_logger

    logger.warning("no configuration yet: %s", "sk-anything-long-enough")

    assert handler.lines == ["WARNING|no configuration yet: sk-anything-long-enough"]



# Maintainer decisions for T5: marker, ignored image key, stack info


def test_t5_redacted_key_is_replaced_by_the_marker(home, redacted_logger):
    """T5 (maintainer decision): the redaction marker is `***`, written where the key was."""
    write_settings(home, _text_and_image())
    logger, handler = redacted_logger

    logger.info("text %s image %s end", FAKE_TEXT_KEY, FAKE_IMAGE_KEY)
    logger.info(f"inline {FAKE_TEXT_KEY}")

    assert handler.lines == ["INFO|text *** image *** end", "INFO|inline ***"]


def test_t5_redacted_exception_text_shows_the_marker(home, redacted_logger):
    """T5 (maintainer decision): in a traceback the key is replaced by `***`."""
    write_settings(home, full_text_settings())
    logger, handler = redacted_logger

    try:
        raise RuntimeError(f"invalid api key {FAKE_TEXT_KEY}")
    except RuntimeError:
        logger.exception("call failed")

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "RuntimeError: invalid api key ***" in output


IGNORED_IMAGE_KEY = "sk-fake-ignored-4444-IGNOREDKEY-not-real-5555"


@pytest.mark.parametrize("text_provider", ["anthropic", "openai"])
def test_rn06_ignored_image_key_is_still_redacted(home, redacted_logger, text_provider):
    """RN-06 / CA-06 / T5 (maintainer decision): an IMAGE_API_KEY ignored for lack of IMAGE_PROVIDER never reaches a log."""
    settings = full_text_settings(provider=text_provider)
    settings["IMAGE_API_KEY"] = IGNORED_IMAGE_KEY
    write_settings(home, settings)
    from core.config import get_config

    assert any(notice.setting == "IMAGE_API_KEY" for notice in get_config().notices)
    logger, handler = redacted_logger

    logger.warning("ignored key %s, text key %s", IGNORED_IMAGE_KEY, FAKE_TEXT_KEY)

    output = _output(handler)
    assert IGNORED_IMAGE_KEY not in output
    assert FAKE_TEXT_KEY not in output
    assert handler.lines == ["WARNING|ignored key ***, text key ***"]


def test_rn06_short_ignored_image_key_changes_nothing(home, redacted_logger):
    """T5: the under-8-characters rule also applies to an ignored image key."""
    settings = full_text_settings(provider="anthropic")
    settings["IMAGE_API_KEY"] = "abc1234"
    write_settings(home, settings)
    logger, handler = redacted_logger

    logger.info("value abc1234")

    assert handler.lines == ["INFO|value abc1234"]


def test_rn06_key_in_stack_info_is_redacted(home):
    """RN-06 / CA-06 / T5 (maintainer decision): a key inside a record's stack_info is redacted."""
    from core.log_redaction import KeyRedactionFilter

    write_settings(home, full_text_settings())
    handler = _CollectingHandler()
    handler.addFilter(KeyRedactionFilter())
    record = logging.LogRecord(
        "t5",
        logging.ERROR,
        __file__,
        1,
        "with stack",
        None,
        None,
        sinfo=f'Stack (most recent call last):\n  File "fake.py", line 3, in call\n    key = "{FAKE_TEXT_KEY}"',
    )

    handler.handle(record)

    output = _output(handler)
    assert FAKE_TEXT_KEY not in output
    assert "Stack (most recent call last):" in output
    assert 'key = "***"' in output


# Records whose arguments do not match the message


@pytest.mark.parametrize(
    ("message", "args"),
    [
        ("key %s %s", (FAKE_TEXT_KEY,)),
        ("key %s", (FAKE_TEXT_KEY, "extra")),
        ("key %(missing)s", ({"auth": FAKE_TEXT_KEY},)),
    ],
    ids=["too-few-args", "too-many-args", "mapping-missing-name"],
)
def test_rn06_ca06_mismatched_args_never_leak_the_key(home, monkeypatch, capsys, message, args):
    """RN-06 / CA-06 / T5: when the message cannot be formatted, the key never reaches stderr through handleError."""
    from core.log_redaction import KeyRedactionFilter

    write_settings(home, full_text_settings())
    monkeypatch.setattr(logging, "raiseExceptions", True)
    stream_handler = logging.StreamHandler(stream=_NullStream())
    stream_handler.addFilter(KeyRedactionFilter())
    logger = logging.getLogger(f"cardfactory.test.t5.mismatch.{uuid.uuid4().hex}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(stream_handler)
    try:
        logger.error(message, *args)
    finally:
        logger.removeHandler(stream_handler)

    captured = capsys.readouterr()
    assert FAKE_TEXT_KEY not in captured.err
    assert FAKE_TEXT_KEY not in captured.out
    assert FAKE_TEXT_KEY not in stream_handler.stream.text


@pytest.mark.parametrize(
    ("message", "args"),
    [
        ("key %s %s", (FAKE_TEXT_KEY,)),
        ("key %(missing)s", ({"auth": FAKE_TEXT_KEY},)),
    ],
    ids=["too-few-args", "mapping-missing-name"],
)
def test_rn06_mismatched_args_record_holds_no_key_after_filtering(home, message, args):
    """RN-06 / T5: after the filter, neither the record's msg nor its args contain the key."""
    from core.log_redaction import KeyRedactionFilter

    write_settings(home, full_text_settings())
    record = logging.LogRecord("t5", logging.ERROR, __file__, 1, message, args, None)

    assert KeyRedactionFilter().filter(record)
    assert FAKE_TEXT_KEY not in str(record.msg)
    assert FAKE_TEXT_KEY not in repr(record.args)


class _NullStream:
    """A text stream that keeps what was written."""

    def __init__(self):
        self.text = ""

    def write(self, text):
        self.text += text

    def flush(self):
        pass
