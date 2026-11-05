"""Debug detection in core.environment (task T1, spec RN-29)."""

import pytest


def _debug_enabled():
    from core.environment import debug_enabled

    return debug_enabled()


def test_t1_debug_disabled_when_variable_absent(monkeypatch):
    """RN-29 / T1: debug_enabled() is False when CARDFACTORY_DEBUG is not set."""
    monkeypatch.delenv("CARDFACTORY_DEBUG", raising=False)

    assert _debug_enabled() is False


@pytest.mark.parametrize("value", ["1", " 1", "1 ", "  1  ", "\t1\n"])
def test_t1_debug_enabled_when_stripped_value_is_1(monkeypatch, value):
    """RN-29 / T1: debug_enabled() is True only when the stripped value equals "1"."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", value)

    assert _debug_enabled() is True


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\t\n", "0", " 0 ", "true", "True", "yes", "on", "2", "01", "1.0", "1 1", "debug"],
)
def test_t1_debug_disabled_for_other_values(monkeypatch, value):
    """RN-29 / T1: any stripped value other than "1" keeps debug_enabled() False."""
    monkeypatch.setenv("CARDFACTORY_DEBUG", value)

    assert _debug_enabled() is False


def test_t1_debug_enabled_is_read_at_call_time(monkeypatch):
    """RN-29 / T1: debug_enabled() follows the variable on every call, not a value cached at import."""
    monkeypatch.delenv("CARDFACTORY_DEBUG", raising=False)
    assert _debug_enabled() is False

    monkeypatch.setenv("CARDFACTORY_DEBUG", "1")
    assert _debug_enabled() is True

    monkeypatch.setenv("CARDFACTORY_DEBUG", "0")
    assert _debug_enabled() is False

    monkeypatch.delenv("CARDFACTORY_DEBUG")
    assert _debug_enabled() is False
