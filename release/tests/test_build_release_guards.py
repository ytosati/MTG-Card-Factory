"""Tests for the release build guards (task T75; spec RN-02, RN-27; plan 9.5). Offline."""

import hashlib
import importlib.util
import io
import subprocess

import pytest

from repo_check_helpers import REPO_ROOT

BUILD_SCRIPT = REPO_ROOT / "release" / "build_release.py"
PAYLOAD = b"fictional embeddable package bytes"


@pytest.fixture
def build():
    spec = importlib.util.spec_from_file_location("build_release_guards", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_git_status(monkeypatch, build, stdout):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")

    monkeypatch.setattr(build.subprocess, "run", fake_run)
    return calls


def test_rn27_dirty_included_paths_stop_the_build(build, monkeypatch, tmp_path):
    """RN-27: uncommitted changes in included paths stop the build before anything runs."""
    calls = fake_git_status(monkeypatch, build, b" M launcher/start.pyw\n?? backend/core/new.py\n")
    with pytest.raises(build.BuildError) as error:
        build.require_clean_tree(tmp_path)
    assert "launcher/start.pyw" in str(error.value)
    command = calls[0]
    assert command[:3] == ["git", "status", "--porcelain"]
    for path in ("backend", "launcher", "frontend", "README.md", "VERSION", "." + "env.example"):
        assert path in command


def test_rn27_clean_tree_passes(build, monkeypatch, tmp_path):
    """RN-27: a clean working tree lets the build go on."""
    fake_git_status(monkeypatch, build, b"")
    build.require_clean_tree(tmp_path)


def pin_for(payload):
    return {"url": "https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip",
            "sha256": hashlib.sha256(payload).hexdigest()}


def serve(monkeypatch, build, payload):
    opened = []

    def fake_urlopen(url, timeout=None):
        opened.append(url)
        return io.BytesIO(payload)

    monkeypatch.setattr(build.urllib.request, "urlopen", fake_urlopen)
    return opened


def test_rn27_mismatching_download_aborts_and_leaves_no_part_file(build, monkeypatch, tmp_path):
    """RN-27: a download whose SHA-256 differs from the pin aborts; no partial file stays."""
    serve(monkeypatch, build, b"tampered bytes")
    with pytest.raises(build.BuildError):
        build.download_python(pin_for(PAYLOAD), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_rn27_cached_file_with_wrong_hash_is_downloaded_again(build, monkeypatch, tmp_path):
    """RN-27: a cached package with a wrong hash is replaced by a fresh, verified download."""
    cached = tmp_path / "python-3.12.10-embed-amd64.zip"
    cached.write_bytes(b"stale bytes")
    opened = serve(monkeypatch, build, PAYLOAD)
    result = build.download_python(pin_for(PAYLOAD), tmp_path)
    assert opened and result == cached
    assert cached.read_bytes() == PAYLOAD
    assert not (tmp_path / "python-3.12.10-embed-amd64.part").exists()


def test_rn27_cached_file_with_matching_hash_is_reused(build, monkeypatch, tmp_path):
    """RN-27: a cached package that matches the pin is used without a download."""
    (tmp_path / "python-3.12.10-embed-amd64.zip").write_bytes(PAYLOAD)
    opened = serve(monkeypatch, build, b"never read")
    build.download_python(pin_for(PAYLOAD), tmp_path)
    assert opened == []
