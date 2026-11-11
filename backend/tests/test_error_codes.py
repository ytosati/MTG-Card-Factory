"""Error codes live in core.errors only (specs/plan.md, section 6)."""

import ast
import re
from pathlib import Path

from core import errors

BACKEND = Path(__file__).resolve().parent.parent
PLAN = BACKEND.parent / "specs" / "plan.md"
SKIPPED_DIRS = {"tests", ".venv", "venv", "migrations", "__pycache__", "node_modules"}
DEFINITION = BACKEND / "core" / "errors.py"


def _plan_codes():
    text = PLAN.read_text(encoding="utf-8")
    start = text.index("never on `message`:") + 20
    end = text.index("`internal`.", start) + 10
    codes = set(re.findall(r"`([a-z_]+)`", text[start:end]))
    # The settings-list code of the same section.
    return codes | {"ignored"}


def _core_codes():
    return {v for k, v in vars(errors).items() if k.startswith("CODE_") and isinstance(v, str)}


def _production_files():
    for path in BACKEND.rglob("*.py"):
        if not SKIPPED_DIRS.intersection(path.relative_to(BACKEND).parts):
            yield path


def _docstring_nodes(tree):
    nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                nodes.add(id(body[0].value))
    return nodes


def _lookup_keys(tree):
    """Constants used as a key lookup, such as `fields.get("validation")`, are not codes."""
    nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            nodes.update(id(arg) for arg in node.args)
    return nodes


def _wire_constants(tree):
    """A provider's own wire codes, kept by its adapter as `_WIRE_*` constants, are not application codes (T154)."""
    nodes = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and all(
            isinstance(t, ast.Name) and t.id.startswith("_WIRE_") for t in node.targets
        ):
            nodes.add(id(node.value))
    return nodes


def test_every_plan_code_exists_in_core():
    missing = _plan_codes() - _core_codes()
    assert not missing, f"Codes of plan section 6 missing from core.errors: {sorted(missing)}"


def test_core_defines_no_code_that_the_plan_lacks():
    assert _core_codes() - _plan_codes() == set()


def test_no_code_literal_outside_core_errors():
    codes = _core_codes()
    found = []
    for path in _production_files():
        if path == DEFINITION:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skipped = _docstring_nodes(tree) | _lookup_keys(tree)
        if path.parent.name == "providers":
            skipped |= _wire_constants(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value in codes and id(node) not in skipped:
                found.append(f"{path.relative_to(BACKEND)}:{node.lineno} {node.value!r}")
    assert not found, "Error code literals outside core/errors.py:\n" + "\n".join(found)


def test_code_constants_are_defined_once():
    names = []
    for path in _production_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign):
                names += [(t.id, path) for t in node.targets if isinstance(t, ast.Name) and t.id.startswith("CODE_")]
    outside = [f"{path.relative_to(BACKEND)}: {name}" for name, path in names if path != DEFINITION]
    assert not outside, "CODE_ constants assigned outside core/errors.py:\n" + "\n".join(outside)


def test_active_job_statuses_are_defined_once():
    owners = []
    for path in _production_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "ACTIVE_STATUSES" for t in node.targets
            ):
                owners.append(path.relative_to(BACKEND).as_posix())
    assert len(owners) == 1, owners


def test_provider_error_codes_reference_core():
    from providers import errors as provider_errors

    assert provider_errors.AuthError.code == errors.CODE_AUTH
    assert provider_errors.QuotaError.code == errors.CODE_QUOTA
    assert provider_errors.ProviderError.code == errors.CODE_PROVIDER_UNAVAILABLE
    assert provider_errors.InvalidResponse.code == errors.CODE_INVALID_RESPONSE
    assert provider_errors.ContentRefused.code == errors.CODE_CONTENT_REFUSED
    assert set(provider_errors.MESSAGES) == {
        errors.CODE_AUTH,
        errors.CODE_QUOTA,
        errors.CODE_RATE_LIMITED,
        errors.CODE_MODEL_NOT_FOUND,
        errors.CODE_PROVIDER_UNAVAILABLE,
        errors.CODE_INVALID_RESPONSE,
        errors.CODE_CONTENT_REFUSED,
        errors.CODE_PROVIDER_REJECTED,
    }


def test_rn10_t154_provider_rejected_is_a_core_code_with_its_plan_name():
    """RN-10 (T154): the code of an unmapped 4xx answer is `provider_rejected` in core.errors."""
    assert errors.CODE_PROVIDER_REJECTED == "provider_rejected"
    assert errors.CODE_PROVIDER_REJECTED in _plan_codes()
