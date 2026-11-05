"""Shared fixtures for the release tests. They run without Django."""

import pytest


@pytest.fixture
def plain_root(tmp_path):
    """An empty folder that is not a git work tree, so the script walks every file."""
    root = tmp_path / "scan-root"
    root.mkdir()
    return root
