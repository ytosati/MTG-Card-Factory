"""Provider factory for text (task T36, spec RN-05, RN-06, RN-07, RN-08, CA-78).

Details: specs/plan.md, sections 5, 8 and 9.2. `providers.factory` is the only
place that turns the configuration into a text adapter and, with the log
filter, the only caller of `Secret.reveal()` in application code.

API under test:

    providers.factory.text_adapter() -> AdapterResult
        Reads the configuration with core.config.get_config() on every call
        (a fix in `.env` takes effect without a restart, RN-08) and never
        calls a provider.

    providers.factory.AdapterResult(adapter, code=None, setting=None, message=None)
        Frozen value. Exactly one of two shapes:
          - an adapter: `adapter` set, `code`, `setting` and `message` None;
          - no adapter: `adapter` None, `code` an error code of plan section 6,
            `message` a fixed text safe to show, `setting` the setting to fix
            or None. The same fields as core.errors.MappedError and the error
            envelope, so callers map it without branching on the provider.

    Codes:
      - `config_invalid`: a text setting (LLM_PROVIDER, LLM_API_KEY, LLM_MODEL)
        is a setting to fix, or `.env` cannot be read (setting `.env`, CA-77).
        Problems in image settings or APP_PORT never block text (RN-08).
      - `provider_not_available_yet`: `anthropic` or `google` with an otherwise
        valid text configuration, until T41 and T42; `setting` is None because
        the value is valid.

    `openai` returns providers.openai_text.OpenAITextAdapter built with the
    revealed text key and LLM_MODEL (`OpenAITextAdapter(api_key, model, send=None)`).

The fixture that replaces the factory with the fake adapter is
`fake_text_adapter` (tests/provider_fixtures.py, registered in conftest.py).

Values are fictional; keys only look like keys. Nothing reaches the network.
"""

import ast
import inspect
from pathlib import Path

import pytest

from tests.config_files import (  # noqa: F401 (clean_environment is a fixture)
    FAKE_AIZA_MODEL_VALUE,
    FAKE_IMAGE_KEY,
    FAKE_TEXT_KEY,
    bump_mtime,
    clean_environment,
    deny_opening,
    full_text_settings,
    write_env,
    write_env_bytes,
    write_settings,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_DIR.parent

TEXT_SETTINGS = ("LLM_PROVIDER", "LLM_API_KEY", "LLM_MODEL")
MODEL = "gpt-fictional-4"

CODE_CONFIG_INVALID = "config_invalid"
CODE_NOT_AVAILABLE_YET = "provider_not_available_yet"

# The only application modules allowed to call Secret.reveal() (plan sections 5 and 8).
REVEAL_ALLOWED = {
    Path("backend/providers/factory.py"),
    # The log filter needs the key values to remove them from log records.
    Path("backend/core/log_redaction.py"),
}

SKIPPED_DIRECTORIES = {"tests", ".venv", "venv", "node_modules", "__pycache__", "data", "runtime", "dist"}


def _factory():
    from providers import factory

    return factory


def _openai_adapter_class():
    from providers.openai_text import OpenAITextAdapter

    return OpenAITextAdapter


class _Recorder:
    """Records each OpenAITextAdapter construction and each attempt to reach the network."""

    def __init__(self):
        self.constructions = []
        self.sends = []


@pytest.fixture
def recorder(monkeypatch):
    """Wraps OpenAITextAdapter.__init__ and replaces the transport's default sender.

    The wrapper is set on the class itself, so it applies however the factory
    imports the class. A send attempt is recorded and fails the call.
    """
    from providers import transport

    adapter_class = _openai_adapter_class()
    original_init = adapter_class.__init__
    signature = inspect.signature(original_init)
    record = _Recorder()

    def recording_init(self, *args, **kwargs):
        bound = signature.bind(self, *args, **kwargs)
        bound.apply_defaults()
        record.constructions.append(dict(bound.arguments))
        original_init(self, *args, **kwargs)

    def refusing_send(*args, **kwargs):
        record.sends.append((args, kwargs))
        raise AssertionError("The factory must not call a provider.")

    monkeypatch.setattr(adapter_class, "__init__", recording_init)
    monkeypatch.setattr(transport, "_send", refusing_send)
    return record


def _configure(home, **overrides):
    """Write a valid OpenAI text configuration with `overrides` (None removes a setting)."""
    settings = full_text_settings(provider="openai", model=MODEL)
    for name, value in overrides.items():
        if value is None:
            settings.pop(name, None)
        else:
            settings[name] = value
    return write_settings(home, settings)


def _assert_no_adapter(result, code, setting):
    assert result.adapter is None
    assert result.code == code
    assert result.setting == setting
    assert isinstance(result.message, str) and result.message.strip()


def _assert_text_is_clean(result, *values):
    """Neither the message nor the text forms of the result show any of `values`."""
    texts = (result.message or "", repr(result), str(result))
    for value in values:
        for text in texts:
            assert value not in text


# --- openai returns its adapter -------------------------------------------------


def test_rn07_openai_returns_the_openai_text_adapter(clean_environment, recorder):
    """RN-07 / T36: `openai` returns the OpenAI adapter, with no error fields."""
    _configure(clean_environment)
    result = _factory().text_adapter()
    assert isinstance(result.adapter, _openai_adapter_class())
    assert result.code is None
    assert result.setting is None
    assert result.message is None


def test_rn05_the_adapter_gets_the_revealed_text_key_and_the_model(clean_environment, recorder):
    """RN-05 / T36: the adapter is built with the key value from `.env` and LLM_MODEL."""
    _configure(clean_environment)
    _factory().text_adapter()
    assert len(recorder.constructions) == 1
    arguments = recorder.constructions[0]
    assert arguments["api_key"] == FAKE_TEXT_KEY
    assert not hasattr(arguments["api_key"], "reveal"), "The adapter gets the key value, not the Secret."
    assert arguments["model"] == MODEL


def test_rn07_the_factory_returns_an_adapter_of_the_text_adapter_protocol(clean_environment, recorder):
    """RN-07 / T36: call sites use the protocol only, never the provider."""
    from providers.base import TextAdapter

    _configure(clean_environment)
    assert isinstance(_factory().text_adapter().adapter, TextAdapter)


def test_rn08_choosing_the_adapter_never_calls_a_provider(clean_environment, recorder):
    """RN-08 / T36: keys are tried only by the connection test and by a generation."""
    _configure(clean_environment)
    _factory().text_adapter()
    assert recorder.sends == []


@pytest.mark.parametrize("written", ["OpenAI", "OPENAI", "  openai  ", '"openai"'])
def test_rn05_the_provider_value_is_read_as_core_config_reads_it(clean_environment, recorder, written):
    """RN-05 / T36: case, spaces and quotes around `openai` still select the OpenAI adapter."""
    write_env(clean_environment, f"LLM_PROVIDER={written}\nLLM_API_KEY={FAKE_TEXT_KEY}\nLLM_MODEL={MODEL}\n")
    assert isinstance(_factory().text_adapter().adapter, _openai_adapter_class())


@pytest.mark.parametrize(
    "model",
    ["gpt-fictional-4-turbo-2099-12-31", "modèle-fictif-ü", "x" * 4000],
    ids=["dated", "non-ascii", "huge"],
)
def test_rn05_model_names_are_free_text_passed_unchanged(clean_environment, recorder, model):
    """RN-05 / T36: model names are not checked against a list; the adapter gets them unchanged."""
    _configure(clean_environment, LLM_MODEL=model)
    result = _factory().text_adapter()
    assert result.adapter is not None
    assert recorder.constructions[0]["model"] == model


def test_rn06_the_result_with_an_adapter_never_shows_the_key(clean_environment, recorder):
    """RN-06 / T36: the result's text forms never contain the key."""
    _configure(clean_environment)
    result = _factory().text_adapter()
    _assert_text_is_clean(result, FAKE_TEXT_KEY)


def test_rn08_image_settings_to_fix_do_not_block_text(clean_environment, recorder):
    """RN-08 / T36: a problem in the image settings makes art unavailable; text keeps working."""
    _configure(
        clean_environment,
        IMAGE_PROVIDER="anthropic",
        IMAGE_MODEL="",
        IMAGE_API_KEY=FAKE_IMAGE_KEY,
    )
    assert isinstance(_factory().text_adapter().adapter, _openai_adapter_class())


def test_ca78_a_key_like_image_model_does_not_block_text(clean_environment, recorder):
    """CA-78 / RN-08 / T36: a key-like IMAGE_MODEL is an image setting to fix; text keeps working."""
    _configure(clean_environment, IMAGE_PROVIDER="openai", IMAGE_MODEL=FAKE_TEXT_KEY)
    assert isinstance(_factory().text_adapter().adapter, _openai_adapter_class())


def test_rn08_an_invalid_port_does_not_block_text(clean_environment, recorder):
    """RN-08 / RN-47 / T36: APP_PORT falls back to the default; text keeps working."""
    _configure(clean_environment, APP_PORT="not-a-port")
    assert isinstance(_factory().text_adapter().adapter, _openai_adapter_class())


def test_rn08_an_ignored_image_key_does_not_replace_the_text_key(clean_environment, recorder):
    """RN-08 / T36: IMAGE_API_KEY with no IMAGE_PROVIDER is ignored; the text adapter uses LLM_API_KEY."""
    _configure(clean_environment, IMAGE_API_KEY=FAKE_IMAGE_KEY)
    _factory().text_adapter()
    assert recorder.constructions[0]["api_key"] == FAKE_TEXT_KEY


# --- invalid configuration: no adapter, setting named ---------------------------


@pytest.mark.parametrize(
    ("overrides", "setting"),
    [
        ({"LLM_PROVIDER": None}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": ""}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": "mistral"}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": "open ai"}, "LLM_PROVIDER"),
        ({"LLM_PROVIDER": "🃏"}, "LLM_PROVIDER"),
        ({"LLM_API_KEY": None}, "LLM_API_KEY"),
        ({"LLM_API_KEY": ""}, "LLM_API_KEY"),
        ({"LLM_MODEL": None}, "LLM_MODEL"),
        ({"LLM_MODEL": ""}, "LLM_MODEL"),
        ({"LLM_MODEL": "   "}, "LLM_MODEL"),
    ],
    ids=[
        "provider-missing",
        "provider-empty",
        "provider-unknown",
        "provider-with-space",
        "provider-emoji",
        "key-missing",
        "key-empty",
        "model-missing",
        "model-empty",
        "model-blank",
    ],
)
def test_ca05_an_invalid_text_setting_returns_no_adapter_and_names_it(
    clean_environment, recorder, overrides, setting
):
    """CA-05 / RN-08 / T36: no adapter, `config_invalid` with the setting to fix, no adapter built."""
    _configure(clean_environment, **overrides)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, setting)
    assert recorder.constructions == []
    assert recorder.sends == []


def test_rn08_the_message_is_the_one_core_config_gives_for_the_setting(clean_environment, recorder):
    """RN-08 / T36: the factory reuses the settings-to-fix message the Status screen shows (T6)."""
    from core.config import get_config

    _configure(clean_environment, LLM_MODEL=None)
    expected = {issue.setting: issue.message for issue in get_config().settings_to_fix}
    assert _factory().text_adapter().message == expected["LLM_MODEL"]


def test_ca05_an_empty_configuration_returns_no_adapter(clean_environment, recorder):
    """CA-05 / T36: with no `.env` at all, a text setting is named and no adapter is built."""
    result = _factory().text_adapter()
    assert result.adapter is None
    assert result.code == CODE_CONFIG_INVALID
    assert result.setting in TEXT_SETTINGS
    assert recorder.constructions == []


def test_ca05_several_invalid_text_settings_name_one_of_them(clean_environment, recorder):
    """CA-05 / T36: with the key and the model missing, the setting named is one of the two."""
    _configure(clean_environment, LLM_API_KEY=None, LLM_MODEL=None)
    result = _factory().text_adapter()
    assert result.adapter is None
    assert result.code == CODE_CONFIG_INVALID
    assert result.setting in {"LLM_API_KEY", "LLM_MODEL"}


def test_rn06_a_key_pasted_as_the_provider_is_never_shown(clean_environment, recorder):
    """RN-06 / RN-08 / T36: a key written in LLM_PROVIDER names the setting without showing the value."""
    pasted = "sk-fake-pasted-into-provider-0000-not-real"
    _configure(clean_environment, LLM_PROVIDER=pasted)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, "LLM_PROVIDER")
    _assert_text_is_clean(result, pasted, FAKE_TEXT_KEY)


def test_rn06_the_no_adapter_result_never_shows_the_key(clean_environment, recorder):
    """RN-06 / T36: a missing model does not lead to the key appearing in the result."""
    _configure(clean_environment, LLM_MODEL=None)
    _assert_text_is_clean(_factory().text_adapter(), FAKE_TEXT_KEY)


def test_ca77_an_unreadable_env_file_names_the_file(clean_environment, recorder):
    """CA-77 / RN-40 / T36: `.env` that is not text returns no adapter and names `.env`."""
    write_env_bytes(clean_environment, "LLM_PROVIDER=openai\n".encode("utf-16-le"))
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, ".env")
    assert recorder.constructions == []


def test_ca77_an_env_file_that_cannot_be_opened_names_the_file(clean_environment, recorder, monkeypatch):
    """CA-77 / RN-40 / T36: a valid `.env` that cannot be opened returns no adapter and names `.env`."""
    path = _configure(clean_environment)
    deny_opening(monkeypatch, path)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, ".env")
    assert recorder.constructions == []


# --- a model value that looks like a key (CA-78) -------------------------------


@pytest.mark.parametrize(
    ("model", "extra"),
    [
        (FAKE_TEXT_KEY, {}),
        (FAKE_IMAGE_KEY, {"IMAGE_PROVIDER": "openai", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": "img-fictional-1"}),
        (FAKE_IMAGE_KEY, {"IMAGE_API_KEY": FAKE_IMAGE_KEY}),
        ("sk-fake-model-pasted-0000-not-real", {}),
        (FAKE_AIZA_MODEL_VALUE, {}),
    ],
    ids=["text-key", "image-key", "ignored-image-key", "sk-prefix", "aiza-prefix"],
)
def test_ca78_a_key_like_model_returns_no_adapter_and_calls_nothing(clean_environment, recorder, model, extra):
    """CA-78 / RN-06 / RN-08 / T36: LLM_MODEL named, no adapter built, no provider call, value never shown."""
    _configure(clean_environment, LLM_MODEL=model, **extra)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, "LLM_MODEL")
    assert recorder.constructions == []
    assert recorder.sends == []
    _assert_text_is_clean(result, model, FAKE_TEXT_KEY, FAKE_IMAGE_KEY)


@pytest.mark.parametrize("provider", ["anthropic", "google"])
def test_ca78_a_key_like_model_is_a_setting_to_fix_for_every_provider(clean_environment, recorder, provider):
    """CA-78 / T36: the key-like model wins over the development state of the other providers."""
    _configure(clean_environment, LLM_PROVIDER=provider, LLM_MODEL=FAKE_TEXT_KEY)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, "LLM_MODEL")
    _assert_text_is_clean(result, FAKE_TEXT_KEY)


# --- anthropic and google until T41 and T42 -------------------------------------


@pytest.mark.parametrize("provider", ["anthropic", "google", "Anthropic", "GOOGLE"])
def test_rn07_anthropic_and_google_are_not_available_yet(clean_environment, recorder, provider):
    """RN-07 / T36: a valid value with no adapter yet: `provider_not_available_yet`, no setting."""
    _configure(clean_environment, LLM_PROVIDER=provider)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_NOT_AVAILABLE_YET, None)
    assert recorder.constructions == []
    assert recorder.sends == []
    _assert_text_is_clean(result, FAKE_TEXT_KEY)


@pytest.mark.parametrize("provider", ["anthropic", "google"])
def test_rn08_an_invalid_setting_wins_over_not_available_yet(clean_environment, recorder, provider):
    """RN-08 / T36: with a missing key, the setting to fix is named before the development state."""
    _configure(clean_environment, LLM_PROVIDER=provider, LLM_API_KEY=None)
    result = _factory().text_adapter()
    _assert_no_adapter(result, CODE_CONFIG_INVALID, "LLM_API_KEY")


# --- the configuration is read on every call -----------------------------------


def test_rn08_a_fix_in_env_takes_effect_without_a_restart(clean_environment, recorder):
    """RN-08 / T36: the factory reads the configuration again on each call."""
    path = _configure(clean_environment, LLM_MODEL=None)
    assert _factory().text_adapter().setting == "LLM_MODEL"
    _configure(clean_environment)
    bump_mtime(path)
    result = _factory().text_adapter()
    assert isinstance(result.adapter, _openai_adapter_class())
    assert recorder.constructions[-1]["model"] == MODEL


def test_rn08_a_replaced_key_is_the_one_the_next_adapter_gets(clean_environment, recorder):
    """RN-08 / T36: a key replaced in `.env` reaches the next adapter."""
    path = _configure(clean_environment)
    _factory().text_adapter()
    replacement = "sk-fake-replacement-4444-not-real-5555"
    _configure(clean_environment, LLM_API_KEY=replacement)
    bump_mtime(path, seconds=20)
    _factory().text_adapter()
    assert [c["api_key"] for c in recorder.constructions] == [FAKE_TEXT_KEY, replacement]


# --- the fake adapter -----------------------------------------------------------


@pytest.mark.parametrize("value", ["fake", "FAKE", "Fake", " fake ", "providers.fake", "FakeTextAdapter", "test"])
def test_t36_the_fake_is_never_selectable_from_env(clean_environment, recorder, value):
    """T36 / plan 9.2: no LLM_PROVIDER value selects the fake; it is a setting to fix."""
    from providers.fake import FakeTextAdapter

    _configure(clean_environment, LLM_PROVIDER=value)
    result = _factory().text_adapter()
    assert not isinstance(result.adapter, FakeTextAdapter)
    _assert_no_adapter(result, CODE_CONFIG_INVALID, "LLM_PROVIDER")


def test_t36_the_factory_module_never_imports_the_fake():
    """T36 / plan 9.2: the fake reaches the factory only through the test fixture."""
    tree = ast.parse((BACKEND_DIR / "providers" / "factory.py").read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.add(module)
            imported.update(f"{module}.{alias.name}" for alias in node.names)
    assert not any(name == "providers.fake" or name.endswith(".fake") for name in imported), imported


def test_t36_the_fixture_replaces_the_factory_with_the_fake(clean_environment, fake_text_adapter):
    """T36 / plan 9.2: with the fixture, `text_adapter()` returns the fake, whatever `.env` holds."""
    from providers.base import Usage
    from providers.fake import FakeTextAdapter

    # No `.env` at all: the real factory would name a setting to fix.
    result = _factory().text_adapter()
    assert result.adapter is fake_text_adapter
    assert isinstance(result.adapter, FakeTextAdapter)
    assert result.code is None and result.setting is None and result.message is None

    schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
    fake_text_adapter.add_response({"name": "Lantern Warden of Vell"}, Usage(input_tokens=12, output_tokens=4))
    data, usage = result.adapter.complete_json("system", [{"role": "user", "content": "idea"}], schema)
    assert data == {"name": "Lantern Warden of Vell"}
    assert usage == Usage(input_tokens=12, output_tokens=4)
    assert len(fake_text_adapter.calls) == 1


def test_t36_the_fixture_returns_the_same_fake_on_every_call(fake_text_adapter):
    """T36: one fake per test, so a test scripts it once and reads all its calls."""
    factory = _factory()
    assert factory.text_adapter().adapter is factory.text_adapter().adapter is fake_text_adapter


def test_t36_without_the_fixture_the_factory_is_the_real_one(clean_environment, recorder):
    """T36: the fixture's replacement does not leak into a test that does not request it."""
    from providers.fake import FakeTextAdapter

    _configure(clean_environment)
    assert not isinstance(_factory().text_adapter().adapter, FakeTextAdapter)


# --- the key is revealed only inside the factory --------------------------------


def _application_sources():
    """Every Python file of the application: backend, launcher and release scripts, not tests."""
    for root in (REPOSITORY_ROOT / "backend", REPOSITORY_ROOT / "launcher", REPOSITORY_ROOT / "release"):
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(REPOSITORY_ROOT)
            if SKIPPED_DIRECTORIES.intersection(relative.parts[:-1]):
                continue
            if relative.name == "conftest.py" or relative.name.startswith("test_"):
                continue
            yield relative, path


def _reveal_uses(path):
    """Line numbers where `path` calls `.reveal()` or reaches it through getattr."""
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr == "reveal":
            lines.append(node.lineno)
        elif (
            isinstance(function, ast.Name)
            and function.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "reveal"
        ):
            lines.append(node.lineno)
    return lines


def test_rn06_only_the_factory_and_the_log_filter_reveal_a_key():
    """RN-06 / T36 / plan 8: no other application module calls Secret.reveal()."""
    offenders = {}
    for relative, path in _application_sources():
        if relative in REVEAL_ALLOWED:
            continue
        lines = _reveal_uses(path)
        if lines:
            offenders[relative.as_posix()] = lines
    assert offenders == {}


def test_rn06_the_factory_is_where_the_text_key_is_revealed():
    """RN-06 / T36: the factory reveals the key itself; the sweep above would be empty otherwise."""
    assert _reveal_uses(BACKEND_DIR / "providers" / "factory.py")


def test_rn06_the_sweep_sees_the_application_modules():
    """T36: the source sweep reads the real application, so an empty result means something."""
    seen = {relative.as_posix() for relative, _ in _application_sources()}
    assert "backend/core/config.py" in seen
    assert "backend/core/log_redaction.py" in seen
    assert not any("/tests/" in name for name in seen)
