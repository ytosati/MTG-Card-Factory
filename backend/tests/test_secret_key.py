"""Django secret key stored in `data/secret_key` (tasks T5 and T7, spec RN-06, RN-40, plan section 8).

API under test: `core.secret_key.get_secret_key()` returns the key stored in
`<home>/data/secret_key`, creating the file (and `data/`) on the first call and
reading it on later calls. Settings use it as `SECRET_KEY`.

Every test uses a temporary application home, never the repository data/.
"""

import os
import stat
import sys

import pytest

from tests.config_files import (
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    clean_environment,  # noqa: F401 (fixture)
    deny_opening,
    write_settings,
)
from tests.settings_probe import BACKEND_DIR, run_probe

PLACEHOLDER = "dev-placeholder-not-secret"

SECRET_PROBE = """
import json
import django
from django.conf import settings
django.setup()
print(json.dumps({"secret_key": settings.SECRET_KEY}))
"""


def _get_secret_key():
    from core.secret_key import get_secret_key

    return get_secret_key()


def _key_file(home):
    return home / "data" / "secret_key"


def _stored(home):
    return _key_file(home).read_text(encoding="utf-8").strip()


@pytest.fixture
def home(clean_environment):  # noqa: F811 (fixture)
    (clean_environment / "data").mkdir()
    return clean_environment


# In-process: core.secret_key


def test_t5_first_call_creates_secret_key_file(home):
    """T5 / plan section 8: the first start writes data/secret_key with a non-empty value."""
    assert not _key_file(home).exists()

    key = _get_secret_key()

    assert isinstance(key, str)
    assert key.strip()
    assert _key_file(home).is_file()
    assert _stored(home) == key


def test_t5_later_calls_reuse_the_same_key(home):
    """T5: later starts read the stored key; the file is not rewritten."""
    first = _get_secret_key()
    content_before = _key_file(home).read_bytes()

    second = _get_secret_key()
    third = _get_secret_key()

    assert first == second == third
    assert _key_file(home).read_bytes() == content_before


def test_t5_existing_key_file_is_read_not_regenerated(home):
    """T5: an existing data/secret_key is read as is and never replaced."""
    stored = "fictional-secret-0123456789-abcdefghij-KLMNOPQRST-uvwxyz"
    _key_file(home).write_text(stored, encoding="utf-8")

    assert _get_secret_key() == stored
    assert _key_file(home).read_text(encoding="utf-8") == stored


def test_t5_missing_data_folder_is_created(clean_environment):  # noqa: F811 (fixture)
    """T5: on the very first start data/ may not exist yet; it is created with the key file."""
    home = clean_environment
    assert not (home / "data").exists()

    key = _get_secret_key()

    assert _key_file(home).is_file()
    assert _stored(home) == key


def test_t5_key_follows_the_current_home(home, tmp_path, monkeypatch):
    """T5 / plan section 7: the key file lives under the current CARDFACTORY_HOME; homes do not share a key."""
    first = _get_secret_key()

    other_home = tmp_path / "other-home"
    other_home.mkdir()
    monkeypatch.setenv("CARDFACTORY_HOME", str(other_home))
    second = _get_secret_key()

    assert _key_file(other_home).is_file()
    assert _stored(other_home) == second
    assert second != first
    assert _stored(home) == first


def test_t5_generated_key_is_not_the_development_placeholder(home):
    """T5: the generated key replaces the T1 development placeholder."""
    assert _get_secret_key() != PLACEHOLDER


def test_rn06_secret_key_file_never_contains_an_api_key(home):
    """RN-06 / plan section 8: the Django secret key is not the API key; the file holds neither key."""
    settings = {
        "LLM_PROVIDER": "anthropic",
        "LLM_API_KEY": FAKE_TEXT_KEY,
        "LLM_MODEL": "fake-text-model-1",
        "IMAGE_PROVIDER": "openai",
        "IMAGE_API_KEY": FAKE_IMAGE_KEY,
        "IMAGE_MODEL": "fake-image-model-1",
    }
    write_settings(home, settings)

    key = _get_secret_key()
    content = _key_file(home).read_text(encoding="utf-8")

    for api_key in (FAKE_TEXT_KEY, FAKE_IMAGE_KEY):
        assert api_key not in key
        assert api_key not in content


# Fresh interpreter: Django settings


@pytest.fixture
def probe(tmp_path):
    workdir = tmp_path / "cwd"
    workdir.mkdir()

    def _run(home):
        overrides = {
            "PYTHONPATH": str(BACKEND_DIR),
            "DJANGO_SETTINGS_MODULE": "cardfactory.settings",
            "CARDFACTORY_HOME": str(home),
        }
        return run_probe(SECRET_PROBE, overrides, cwd=workdir)

    return _run


def test_t5_settings_secret_key_comes_from_the_data_file(probe, tmp_path):
    """T5: settings.SECRET_KEY is the value stored in <home>/data/secret_key, not the placeholder."""
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)

    result = probe(home)

    assert result["secret_key"] != PLACEHOLDER
    assert _key_file(home).is_file()
    assert _stored(home) == result["secret_key"]


def test_t5_settings_reuse_the_key_on_the_next_start(probe, tmp_path):
    """T5: two starts on the same home see the same SECRET_KEY."""
    home = tmp_path / "home"
    (home / "data").mkdir(parents=True)

    first = probe(home)["secret_key"]
    second = probe(home)["secret_key"]

    assert first != PLACEHOLDER
    assert first == second


def test_t5_settings_create_data_folder_on_first_start(probe, tmp_path):
    """T5: starting with a home that has no data/ yet creates data/secret_key."""
    home = tmp_path / "home"
    home.mkdir()

    result = probe(home)

    assert _key_file(home).is_file()
    assert _stored(home) == result["secret_key"]


# Maintainer decisions for T5: empty file, key strength


@pytest.mark.parametrize("content", ["", "   ", "\n", " \t\r\n "], ids=["empty", "spaces", "newline", "mixed-whitespace"])
def test_t5_empty_or_whitespace_key_file_is_replaced(home, content):
    """T5 (maintainer decision): an empty or whitespace-only secret_key is replaced by a new key and rewritten."""
    _key_file(home).write_text(content, encoding="utf-8", newline="")

    key = _get_secret_key()

    assert key.strip() == key
    assert len(key) >= 50
    assert _stored(home) == key
    assert _get_secret_key() == key


def test_t5_key_file_content_is_used_stripped(home):
    """T5 (maintainer decision): a key file with content is used as is, without surrounding whitespace."""
    stored = "fictional-secret-with-padding-0123456789-ABCDEFGHIJKLMNOP"
    _key_file(home).write_text(f"  {stored}\r\n\t", encoding="utf-8", newline="")

    assert _get_secret_key() == stored
    assert _key_file(home).read_bytes() == f"  {stored}\r\n\t".encode("utf-8")


def test_t5_generated_key_passes_django_strength_check(home):
    """T5 (maintainer decision, Django check W009): at least 50 characters and at least 5 distinct ones."""
    key = _get_secret_key()

    assert len(key) >= 50
    assert len(set(key)) >= 5
    assert not key.startswith("django-insecure-")


# T7: content that is not UTF-8, and a file that cannot be read or written (plan section 8)


def _startup_message(error):
    return f"{error.problem}\n{error.fix}".replace("\\", "/")


def _assert_names_the_key_file(error):
    assert "data/secret_key" in _startup_message(error)
    assert "check its permissions, or delete it" in error.fix.lower()


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfe\x80\x81",
        b"fictional-secret-0123456789-abcdefghij-\x80-KLMNOPQRST-uvwxyz",
        "fictional-secret-0123456789-abcdefghij-KLMNOPQRST".encode("utf-16"),
        b"\xc3",
        b"\xed\xa0\x80",
    ],
    ids=["invalid-bytes", "stray-byte-in-a-key", "utf-16-with-bom", "truncated-sequence", "encoded-surrogate"],
)
def test_t7_rn40_key_file_that_is_not_utf8_is_replaced(home, content):
    """RN-40 / T7 (plan section 8): a secret_key whose content is not UTF-8 is replaced by a new valid key."""
    _key_file(home).write_bytes(content)

    key = _get_secret_key()

    assert key.strip() == key
    assert len(key) >= 50
    assert _key_file(home).read_bytes() != content
    assert _stored(home) == key
    assert _get_secret_key() == key


def test_t7_rn40_key_file_that_is_a_folder_is_a_startup_error(home):
    """RN-40 / T7 (plan section 8): a folder named data/secret_key raises StartupError naming the file and the fix."""
    from core.startup import StartupError

    _key_file(home).mkdir()
    (_key_file(home) / "fictional-note.txt").write_text("not a key", encoding="utf-8")

    with pytest.raises(StartupError) as raised:
        _get_secret_key()

    _assert_names_the_key_file(raised.value)
    assert _key_file(home).is_dir()


def test_t7_rn40_key_file_that_cannot_be_read_is_a_startup_error(home, monkeypatch):
    """RN-40 / T7 (plan section 8): a data/secret_key that cannot be opened raises StartupError naming the file."""
    from core.startup import StartupError

    stored = "fictional-secret-0123456789-abcdefghij-KLMNOPQRST-uvwxyz"
    _key_file(home).write_text(stored, encoding="utf-8")
    deny_opening(monkeypatch, _key_file(home))

    with pytest.raises(StartupError) as raised:
        _get_secret_key()

    _assert_names_the_key_file(raised.value)
    assert stored not in _startup_message(raised.value)


def test_t7_rn40_unreadable_key_file_is_not_replaced(home, monkeypatch):
    """RN-40 / T7 (plan section 8): a key file that cannot be read is reported, never overwritten."""
    from core.startup import StartupError

    stored = "fictional-secret-0123456789-abcdefghij-KLMNOPQRST-uvwxyz"
    _key_file(home).write_text(stored, encoding="utf-8")
    denial = deny_opening(monkeypatch, _key_file(home))

    with pytest.raises(StartupError):
        _get_secret_key()

    denial.allow()
    assert _key_file(home).read_text(encoding="utf-8") == stored


@pytest.fixture
def read_only_key_file(home):
    """data/secret_key made read-only (and data/ too where the system honors it); restored afterwards."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("permissions do not apply to the root user")
    path = _key_file(home)
    folder = path.parent

    def _make(content):
        path.write_bytes(content)
        os.chmod(path, stat.S_IREAD)
        if sys.platform != "win32":
            # A write through a temporary file and a rename needs the folder.
            os.chmod(folder, stat.S_IREAD | stat.S_IEXEC)
        return path

    yield _make
    if sys.platform != "win32":
        os.chmod(folder, stat.S_IRWXU)
    if path.exists():
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)


@pytest.mark.parametrize(
    "content",
    [b"", b"  \r\n", b"\xff\xfe\x80\x81"],
    ids=["empty", "whitespace", "not-utf8"],
)
def test_t7_rn40_key_file_that_cannot_be_written_is_a_startup_error(read_only_key_file, content):
    """RN-40 / T7 (plan section 8): a key file that must be replaced but cannot be written raises StartupError."""
    from core.startup import StartupError

    path = read_only_key_file(content)

    with pytest.raises(StartupError) as raised:
        _get_secret_key()

    _assert_names_the_key_file(raised.value)
    assert path.read_bytes() == content


def test_t7_rn40_read_only_file_with_a_valid_key_is_read(read_only_key_file):
    """RN-40 / T7 (plan section 8): a read-only file with a valid key is read; it is never rewritten."""
    stored = "fictional-secret-0123456789-abcdefghij-KLMNOPQRST-uvwxyz"
    read_only_key_file(stored.encode("utf-8"))

    assert _get_secret_key() == stored


STARTUP_ERROR_PROBE = """
import json
import django
from core.startup import StartupError
try:
    django.setup()
except StartupError as error:
    print(json.dumps({"startup_error": True, "problem": error.problem, "fix": error.fix}))
else:
    print(json.dumps({"startup_error": False}))
"""


def test_t7_rn40_settings_load_raises_startup_error_for_a_key_folder(tmp_path):
    """RN-40 / T7 (plan 8 and 9.5, step 4): loading the settings with a folder at data/secret_key raises StartupError."""
    home = tmp_path / "home"
    (home / "data" / "secret_key").mkdir(parents=True)
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    overrides = {
        "PYTHONPATH": str(BACKEND_DIR),
        "DJANGO_SETTINGS_MODULE": "cardfactory.settings",
        "CARDFACTORY_HOME": str(home),
    }

    result = run_probe(STARTUP_ERROR_PROBE, overrides, cwd=workdir)

    assert result["startup_error"] is True
    assert "data/secret_key" in f"{result['problem']}\n{result['fix']}".replace("\\", "/")
    assert "check its permissions, or delete it" in result["fix"].lower()
