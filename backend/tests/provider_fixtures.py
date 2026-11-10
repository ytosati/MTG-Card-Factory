"""Test helper: replaces the provider factory functions with the fake adapter.

Plan section 9.2: tests replace the factory functions with a pytest fixture
that returns the fake adapter; the fake is never selectable from `.env`. The
fixture is registered in `tests/conftest.py`, so every test can request it:

    def test_something(fake_text_adapter):
        fake_text_adapter.add_response({"name": "Lantern Warden of Vell"}, Usage(10, 5))
        ...  # code that calls providers.factory.text_adapter()

The replacement is set on the `providers.factory` module, so call sites must
look the function up there when they run (`factory.text_adapter()`), not bind
it at import time.
"""

import pytest


@pytest.fixture
def fake_text_adapter(monkeypatch):
    """A FakeTextAdapter returned by every `providers.factory.text_adapter()` call of the test."""
    from providers import factory
    from providers.fake import FakeTextAdapter

    adapter = FakeTextAdapter()

    def _fake_text_adapter():
        return factory.AdapterResult(adapter=adapter)

    monkeypatch.setattr(factory, "text_adapter", _fake_text_adapter)
    return adapter
