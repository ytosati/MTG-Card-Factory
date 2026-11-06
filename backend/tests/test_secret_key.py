"""Django secret key stored in `data/secret_key` (task T5, spec RN-06, plan section 8).

API under test: `core.secret_key.get_secret_key()` returns the key stored in
`<home>/data/secret_key`, creating the file (and `data/`) on the first call and
reading it on later calls. Settings use it as `SECRET_KEY`.

Every test uses a temporary application home, never the repository data/.
"""

import pytest

from tests.config_files import (
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    clean_environment,  # noqa: F401 (fixture)
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
