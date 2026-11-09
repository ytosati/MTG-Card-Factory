"""Where the built frontend is found (task T10, spec RN-27, plan sections 2, 7 and 9.5).

Contract under test: `core.paths.frontend_build_dir(code_root=None)` returns the
absolute path of the built frontend folder (the one that holds `index.html` and
`assets/`), whether or not it exists yet.

- `code_root` is the folder that holds `backend/`; by default the one this code
  runs from (`core.paths.REPOSITORY_ROOT`). The application home
  (`CARDFACTORY_HOME`, which holds `.env` and `data/`) does not move it.
- Clone or development layout: `<root>/frontend/` is the frontend source (with
  `package.json`, `src/` and Vite's source `index.html`); the build is
  `<root>/frontend/dist`.
- Zip layout (plan 9.5): `<zip>/app/backend/` and `<zip>/app/frontend/` (built);
  code root is `<zip>/app`, and the build is `<zip>/app/frontend`.

The Django setting `FRONTEND_BUILD_DIR` defaults to `frontend_build_dir()`.
Layouts are fictional folders written in a temporary directory.
"""

from pathlib import Path

import pytest

from tests.frontend_build import BUILD_DIR_SETTING, write_build


def _frontend_build_dir(*args, **kwargs):
    from core import paths

    return paths.frontend_build_dir(*args, **kwargs)


def _clone_layout(root, built=True):
    """A clone: backend source, frontend source with Vite's own index.html, optional dist."""
    (root / "backend" / "core").mkdir(parents=True)
    (root / "backend" / "manage.py").write_text("# fictional\n", encoding="utf-8")
    frontend = root / "frontend"
    (frontend / "src").mkdir(parents=True)
    (frontend / "package.json").write_text('{"name": "fixture-frontend"}\n', encoding="utf-8")
    (frontend / "index.html").write_text(
        '<!doctype html><script type="module" src="/src/main.tsx"></script>\n', encoding="utf-8"
    )
    (frontend / "src" / "main.tsx").write_text("export {};\n", encoding="utf-8")
    (root / "launcher").mkdir()
    (root / "start.cmd").write_text("@echo off\n", encoding="utf-8")
    if built:
        write_build(frontend / "dist")
    return root


def _zip_layout(extracted):
    """The release zip after extraction (plan 9.5); returns the code root `<zip>/app`."""
    (extracted / "python").mkdir(parents=True)
    app = extracted / "app"
    (app / "backend" / "core").mkdir(parents=True)
    (app / "backend" / "manage.py").write_text("# fictional\n", encoding="utf-8")
    write_build(app / "frontend")
    (extracted / "launcher").mkdir()
    (extracted / "Start Card Factory.cmd").write_text("@echo off\n", encoding="utf-8")
    (extracted / ".env").write_text("LLM_PROVIDER=openai\n", encoding="utf-8")
    (extracted / "data").mkdir()
    return app


def test_t10_rn27_clone_layout_resolves_frontend_dist(tmp_path):
    """RN-27 / T10: in a clone or in development, the built folder is frontend/dist."""
    root = _clone_layout(tmp_path / "clone")

    assert _frontend_build_dir(root) == root / "frontend" / "dist"


def test_t10_rn27_clone_without_build_still_points_at_dist_not_the_source(tmp_path):
    """RN-27 / T10: before the build step, the path is still frontend/dist; the Vite source
    index.html in frontend/ is never taken for the built one."""
    root = _clone_layout(tmp_path / "clone", built=False)

    result = _frontend_build_dir(root)

    assert result == root / "frontend" / "dist"
    assert result != root / "frontend"


def test_t10_rn27_zip_layout_resolves_app_frontend(tmp_path):
    """RN-27 / T10 / plan 9.5: in the extracted zip, the built folder is app/frontend/."""
    extracted = tmp_path / "Card Factory 1.0.0"
    code_root = _zip_layout(extracted)

    assert _frontend_build_dir(code_root) == extracted / "app" / "frontend"


@pytest.mark.parametrize(
    "folder_name",
    ["Card Factory ✓ v0", "café & cartas (2)", "x" * 60, "-1", "0"],
)
def test_t10_rn27_zip_layout_in_an_odd_folder_name(tmp_path, folder_name):
    """RN-27 / T10: the zip resolves its build wherever it is extracted, whatever the folder name."""
    extracted = tmp_path / folder_name
    code_root = _zip_layout(extracted)

    assert _frontend_build_dir(code_root) == extracted / "app" / "frontend"


def test_t10_resolved_build_folder_is_absolute(tmp_path, monkeypatch):
    """T10: the path is absolute, so it does not follow the current working directory."""
    root = _clone_layout(tmp_path / "clone")
    monkeypatch.chdir(tmp_path)

    assert _frontend_build_dir(root).is_absolute()
    assert _frontend_build_dir().is_absolute()


def test_t10_default_code_root_is_where_the_backend_runs_from():
    """T10: with no argument, the build is resolved from the code this backend runs from; this
    repository is a clone, so it is <repository>/frontend/dist, built or not."""
    from core import paths

    assert _frontend_build_dir() == paths.REPOSITORY_ROOT / "frontend" / "dist"
    assert _frontend_build_dir() == _frontend_build_dir(paths.REPOSITORY_ROOT)


def test_t10_application_home_does_not_move_the_build_folder(tmp_path, monkeypatch):
    """Plan section 7 / T10: CARDFACTORY_HOME locates .env and data/, not the built frontend."""
    from core import paths

    other_home = tmp_path / "other-home"
    (other_home / "app" / "frontend").mkdir(parents=True)
    (other_home / "frontend" / "dist").mkdir(parents=True)
    monkeypatch.setenv("CARDFACTORY_HOME", str(other_home))

    assert _frontend_build_dir() == paths.REPOSITORY_ROOT / "frontend" / "dist"


def test_t10_django_setting_defaults_to_the_resolved_build_folder():
    """T10: the serving views use the Django setting FRONTEND_BUILD_DIR, which defaults to
    core.paths.frontend_build_dir()."""
    from django.conf import settings

    assert hasattr(settings, BUILD_DIR_SETTING), f"Django settings must define {BUILD_DIR_SETTING}."
    assert Path(getattr(settings, BUILD_DIR_SETTING)) == _frontend_build_dir()
