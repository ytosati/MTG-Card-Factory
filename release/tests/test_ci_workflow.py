"""Tests for the CI workflow that runs every test suite on push and pull request (task T86).

The workflow is read as text with the standard library, since no YAML library is approved.
"""

import re

import pytest

from workflow_helpers import (
    WORKFLOW_NAME,
    WorkflowSyntaxError,
    is_backend_pytest,
    is_frontend_test,
    is_launcher_release_pytest,
    is_npm_ci,
    is_type_check,
    job_commands,
    jobs,
    load_workflow,
    parse_workflow,
    pip_extra_packages,
    pip_requirement_files,
    read_workflow_text,
    steps,
    suite_failure_problems,
    trigger_names,
    walk,
)

DEV_REQUIREMENTS = "backend/requirements-dev.txt"
RUNTIME_REQUIREMENTS = "backend/requirements.txt"
MINIMUM_NODE = (22, 22, 2)
ACTION_REF = re.compile(r"^actions/[A-Za-z0-9_.-]+@(v\d+(\.\d+){0,2}|[0-9a-f]{40})$")
SUITES = {
    "pytest -q (from backend/)": is_backend_pytest,
    "pytest launcher release (from the repository root)": is_launcher_release_pytest,
    "npm run test (from frontend/)": is_frontend_test,
    "npx tsc -b (from frontend/)": is_type_check,
}


@pytest.fixture(scope="module")
def workflow():
    return load_workflow()


@pytest.fixture(scope="module")
def workflow_text():
    return read_workflow_text()


def all_commands(workflow):
    for job_id, job in jobs(workflow).items():
        for position, cwd, tokens in job_commands(workflow, job):
            yield job_id, position, cwd, tokens


def jobs_running(workflow, matcher):
    return {
        job_id
        for job_id, job in jobs(workflow).items()
        if any(matcher(cwd, tokens) for _, cwd, tokens in job_commands(workflow, job))
    }


def action_steps(job, action):
    return [step for step in steps(job) if isinstance(step, dict) and str(step.get("uses", "")).startswith(f"{action}@")]


def step_input(step, name):
    inputs = step.get("with")
    return inputs.get(name) if isinstance(inputs, dict) else None


# Syntax and structure


def test_t86_workflow_file_exists():
    """T86: the test workflow lives under .github/workflows/."""
    read_workflow_text()


def test_t86_workflow_indentation_uses_spaces_only(workflow_text):
    """T86 syntax check: no tab characters anywhere, since YAML indentation forbids them."""
    assert "\t" not in workflow_text, f"{WORKFLOW_NAME} contains a tab"


def test_t86_workflow_passes_syntax_check(workflow):
    """T86 syntax check: the file reads as block-style YAML with name, on and jobs at the top level."""
    assert isinstance(workflow, dict)
    for key in ("name", "on", "jobs"):
        assert key in workflow, f"{WORKFLOW_NAME} has no top-level '{key}'"
    assert isinstance(workflow["name"], str) and workflow["name"].strip()
    assert jobs(workflow), "the workflow defines no jobs"


def test_t86_every_job_runs_steps_on_a_runner(workflow):
    """T86 syntax check: each job names a runner and has steps, each step either uses an action or runs commands."""
    for job_id, job in jobs(workflow).items():
        assert isinstance(job, dict), f"job {job_id} is not a mapping"
        assert job.get("runs-on"), f"job {job_id} has no runs-on"
        job_steps = steps(job)
        assert job_steps, f"job {job_id} has no steps"
        for step in job_steps:
            assert isinstance(step, dict), f"job {job_id} has a step that is not a mapping"
            assert ("uses" in step) != ("run" in step), f"job {job_id}: a step needs exactly one of uses or run: {step}"


# Triggers


def test_t86_runs_on_every_push_and_pull_request(workflow):
    """T86: the workflow runs on every push and every pull request, with no branch, tag or path filter."""
    triggers = trigger_names(workflow)
    for name in ("push", "pull_request"):
        assert name in triggers, f"the workflow does not run on {name}"
        settings = triggers[name]
        if isinstance(settings, dict):
            filters = {"branches", "branches-ignore", "tags", "tags-ignore", "paths", "paths-ignore"} & set(settings)
            assert not filters, f"{name} is limited by {sorted(filters)}"
        else:
            assert settings in (None, ""), f"unexpected settings for {name}: {settings!r}"


def test_t86_does_not_use_pull_request_target(workflow):
    """T86: pull requests from forks never run with the base repository's permissions."""
    assert "pull_request_target" not in trigger_names(workflow)


# The four suites


@pytest.mark.parametrize("suite", sorted(SUITES))
def test_t86_runs_each_test_suite_in_its_folder(workflow, suite):
    """T86: pytest -q, pytest launcher release, npm run test and npx tsc -b each run, from the folder the plan names."""
    matcher = SUITES[suite]
    assert jobs_running(workflow, matcher), f"the workflow does not run {suite}"


# Python


def test_t86_python_jobs_set_up_python_312(workflow):
    """T86 (plan 13): every job that runs pytest sets up Python 3.12."""
    python_jobs = jobs_running(workflow, is_backend_pytest) | jobs_running(workflow, is_launcher_release_pytest)
    assert python_jobs, "no job runs pytest"
    for job_id in python_jobs:
        setups = action_steps(jobs(workflow)[job_id], "actions/setup-python")
        assert setups, f"job {job_id} runs pytest without actions/setup-python"
        for step in setups:
            version = str(step_input(step, "python-version") or "")
            assert re.fullmatch(r"3\.12(\.\d+)?", version), f"job {job_id} sets up Python {version!r}, not 3.12"


def test_t86_python_jobs_install_the_pinned_requirements_before_pytest(workflow):
    """T86: every job that runs pytest installs backend/requirements-dev.txt (which includes the runtime pins) first."""
    for job_id, job in jobs(workflow).items():
        commands = job_commands(workflow, job)
        test_positions = [
            position
            for position, cwd, tokens in commands
            if is_backend_pytest(cwd, tokens) or is_launcher_release_pytest(cwd, tokens)
        ]
        if not test_positions:
            continue
        install_positions = [
            position
            for position, cwd, tokens in commands
            if DEV_REQUIREMENTS in (pip_requirement_files(cwd, tokens) or [])
        ]
        assert install_positions, f"job {job_id} runs pytest without installing {DEV_REQUIREMENTS}"
        assert min(install_positions) < min(test_positions), f"job {job_id} runs pytest before installing {DEV_REQUIREMENTS}"


def test_t86_pip_installs_only_the_pinned_requirement_files(workflow):
    """T86 (plan 13): pip reads only the pinned backend requirement files and adds no package of its own."""
    for job_id, _, cwd, tokens in all_commands(workflow):
        files = pip_requirement_files(cwd, tokens)
        if files is None:
            continue
        assert set(files) <= {DEV_REQUIREMENTS, RUNTIME_REQUIREMENTS}, f"job {job_id} installs from {files}"
        assert not pip_extra_packages(tokens), f"job {job_id} installs unpinned packages: {pip_extra_packages(tokens)}"


# Node


def _node_version(text):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def test_t86_frontend_jobs_set_up_a_pinned_node_satisfying_engines(workflow):
    """T86 (plan 13): Node is pinned to an exact version at or above 22.22.2, the engines range of package.json."""
    frontend_jobs = jobs_running(workflow, is_frontend_test) | jobs_running(workflow, is_type_check)
    assert frontend_jobs, "no job runs the frontend checks"
    for job_id in frontend_jobs:
        setups = action_steps(jobs(workflow)[job_id], "actions/setup-node")
        assert setups, f"job {job_id} runs npm without actions/setup-node"
        for step in setups:
            raw = step_input(step, "node-version")
            version = _node_version(raw)
            assert version, f"job {job_id}: node-version {raw!r} is not an exact version such as 22.22.2"
            assert version >= MINIMUM_NODE, f"job {job_id}: Node {raw} is below 22.22.2"


def test_t86_frontend_jobs_install_from_the_lockfile_before_testing(workflow):
    """T86: the frontend jobs run npm ci in frontend/ (lockfile-exact) before the tests and the type check."""
    for job_id, job in jobs(workflow).items():
        commands = job_commands(workflow, job)
        check_positions = [
            position for position, cwd, tokens in commands if is_frontend_test(cwd, tokens) or is_type_check(cwd, tokens)
        ]
        if not check_positions:
            continue
        ci_positions = [position for position, cwd, tokens in commands if is_npm_ci(cwd, tokens)]
        assert ci_positions, f"job {job_id} runs the frontend checks without npm ci in frontend/"
        assert min(ci_positions) < min(check_positions), f"job {job_id} runs the frontend checks before npm ci"


def test_t86_never_runs_npm_install(workflow):
    """T86: npm install can change the lockfile and add packages; the workflow uses npm ci only."""
    for job_id, _, _, tokens in all_commands(workflow):
        assert tokens[:2] not in (["npm", "install"], ["npm", "i"], ["npm", "add"]), f"job {job_id} runs {tokens}"


# Safety


def test_t86_uses_no_secrets(workflow_text):
    """T86, CLAUDE.md: the tests need no secret, so the workflow reads none."""
    assert not re.search(r"\bsecrets\s*[.\[]", workflow_text), "the workflow reads a secret"


def test_t86_writes_no_settings_file_and_no_provider_key(workflow_text):
    """CLAUDE.md: CI never creates the settings file or sets a provider key; tests use the fake provider."""
    assert not re.search(r"(?<![\w-])\.env(?!\.example\b)(?![\w-])", workflow_text), "the workflow refers to a .env file"
    for name in ("LLM_API_KEY", "IMAGE_API_KEY"):
        assert name not in workflow_text, f"the workflow sets {name}"


def test_t86_permissions_are_read_only(workflow):
    """T86: the workflow token can only read the repository contents."""
    assert workflow.get("permissions") == {"contents": "read"}, f"top-level permissions: {workflow.get('permissions')!r}"
    for job_id, job in jobs(workflow).items():
        permissions = job.get("permissions") if isinstance(job, dict) else None
        if permissions is None:
            continue
        assert isinstance(permissions, dict), f"job {job_id} permissions: {permissions!r}"
        assert set(permissions.values()) <= {"read", "none"}, f"job {job_id} grants {permissions}"


def test_t86_actions_are_official_and_pinned(workflow):
    """T86: only actions/* actions, each pinned to a version tag (vN, vN.N, vN.N.N) or a full commit SHA, never a branch."""
    found = False
    for job_id, job in jobs(workflow).items():
        assert "uses" not in job, f"job {job_id} calls a reusable workflow"
        for step in steps(job):
            if isinstance(step, dict) and "uses" in step:
                found = True
                assert ACTION_REF.match(str(step["uses"])), f"job {job_id}: action {step['uses']!r} is not pinned"
    assert found, "the workflow uses no action, so it cannot set up Python or Node"


def test_t86_contract_samples_are_only_compared(workflow, workflow_text):
    """Plan 6: in CI the contract samples are compared, never rewritten. GitHub sets CI=true; the workflow keeps it."""
    assert "CARDFACTORY_UPDATE_CONTRACT" not in workflow_text, "the workflow turns on the contract update switch"
    for node in walk(workflow):
        env = node.get("env")
        if isinstance(env, dict) and "CI" in env:
            assert str(env["CI"]).strip().lower() not in {"", "0", "false"}, f"the workflow turns CI off: {env}"


def test_t86_a_failing_suite_fails_its_job(workflow):
    """T86: each suite runs alone in its step, with no condition, no tolerated error and no `|| exit 0`."""
    assert suite_failure_problems(workflow) == []


def test_t86_checkout_does_not_keep_the_token(workflow):
    """T86: every checkout sets persist-credentials: false, so later steps cannot reuse the workflow token."""
    checkouts = [
        (job_id, step)
        for job_id, job in jobs(workflow).items()
        for step in steps(job)
        if isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    assert checkouts, "the workflow never checks out the repository"
    for job_id, step in checkouts:
        value = str(step_input(step, "persist-credentials")).strip().lower()
        assert value == "false", f"job {job_id}: checkout keeps the credentials (persist-credentials: {value})"


def test_t86_run_scripts_interpolate_no_expression(workflow):
    """T86: no run script expands ${{ }}, so pull request text (branch names, titles) never becomes shell code."""
    for job_id, job in jobs(workflow).items():
        for step in steps(job):
            if isinstance(step, dict) and isinstance(step.get("run"), str):
                assert "${{" not in step["run"], f"job {job_id}: run script interpolates an expression: {step['run']!r}"


# The reader itself, so the checks above cannot pass on a misread file


VALID_SAMPLE = """\
name: Sample
on:
  push:
  pull_request:
permissions:
  contents: read
jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4  # a comment
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: |
          python -m pip install -r requirements-dev.txt
          pytest -q
  frontend:
    runs-on: ubuntu-latest
    steps:
      - name: "Set up: Node"
        uses: actions/setup-node@v4
        with:
          node-version: 22.22.2
      - name: Install and check
        run: cd frontend && npm ci && npm run test && npx tsc -b
"""


def test_t86_reader_accepts_a_valid_sample():
    """T86 helper: the reader understands the block style a workflow uses."""
    parsed = parse_workflow(VALID_SAMPLE)
    assert trigger_names(parsed).keys() == {"push", "pull_request"}
    backend = jobs(parsed)["backend"]
    assert steps(backend)[1]["with"]["python-version"] == "3.12"
    commands = [(cwd, tokens) for _, cwd, tokens in job_commands(parsed, backend)]
    assert ("backend", ["pip", "install", "-r", "requirements-dev.txt"]) in commands
    assert pip_requirement_files("backend", ["pip", "install", "-r", "requirements-dev.txt"]) == [DEV_REQUIREMENTS]
    assert any(is_backend_pytest(cwd, tokens) for cwd, tokens in commands)
    frontend = [(cwd, tokens) for _, cwd, tokens in job_commands(parsed, jobs(parsed)["frontend"])]
    assert any(is_npm_ci(cwd, tokens) for cwd, tokens in frontend)
    assert any(is_frontend_test(cwd, tokens) for cwd, tokens in frontend)
    assert any(is_type_check(cwd, tokens) for cwd, tokens in frontend)
    assert steps(jobs(parsed)["frontend"])[0]["name"] == "Set up: Node"


@pytest.mark.parametrize(
    "text",
    [
        "",
        "name: x\njobs:\n\tbuild:\n",
        "name: x\n  jobs: y\n",
        "name: x\nname: y\n",
        "name: x\njobs: {build: {}}\n",
        "name: 'unclosed\n",
        "jobs:\n  a:\n    steps:\n      - run: x\n     - run: y\n",
        "name: x\nthis line is not a key\n",
        "name: Set up: Node\n",
        "jobs:\n  a:\n    steps:\n      - name: Set up: Node\n",
    ],
    ids=[
        "empty",
        "tab",
        "bad-indent",
        "duplicate-key",
        "flow-mapping",
        "unclosed-quote",
        "misaligned-item",
        "not-a-key",
        "plain-value-with-colon",
        "plain-step-name-with-colon",
    ],
)
def test_t86_reader_rejects_malformed_text(text):
    """T86 helper: tabs, stray indentation, duplicate keys, unquoted ': ' and unsupported forms fail the syntax check."""
    with pytest.raises(WorkflowSyntaxError):
        parse_workflow(text)


STRICT_SAMPLE = """\
name: Sample
on:
  push:
  pull_request:
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - name: Backend tests
        working-directory: backend
        run: python -m pytest -q
      - run: pytest launcher release
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - run: npm run test
      - run: npx tsc -b
"""

LOOSE_SAMPLES = {
    "or-exit-0": STRICT_SAMPLE.replace("run: python -m pytest -q", "run: python -m pytest -q || exit 0"),
    "exit-0-on-next-line": STRICT_SAMPLE.replace(
        "run: python -m pytest -q", "run: |\n          python -m pytest -q\n          exit 0"
    ),
    "semicolon-chain": STRICT_SAMPLE.replace("run: npx tsc -b", "run: npx tsc -b; echo done"),
    "and-chain": STRICT_SAMPLE.replace("run: npm run test", "run: npm run test && echo done"),
    "step-continue-on-error": STRICT_SAMPLE.replace(
        "      - run: pytest launcher release", "      - run: pytest launcher release\n        continue-on-error: true"
    ),
    "job-continue-on-error": STRICT_SAMPLE.replace(
        "    runs-on: ubuntu-latest\n    defaults:", "    runs-on: ubuntu-latest\n    continue-on-error: true\n    defaults:"
    ),
    "step-if-false": STRICT_SAMPLE.replace(
        "      - run: npx tsc -b", "      - run: npx tsc -b\n        if: false"
    ),
}


def test_t86_strict_sample_has_no_suite_failure_problem():
    """T86 helper: one suite command per step, with no condition or tolerated error, passes the check."""
    assert suite_failure_problems(parse_workflow(STRICT_SAMPLE)) == []


@pytest.mark.parametrize("name", sorted(LOOSE_SAMPLES))
def test_t86_suite_failure_check_catches_hidden_failures(name):
    """T86 helper: `|| exit 0`, chained commands, continue-on-error and `if: false` are all caught."""
    assert suite_failure_problems(parse_workflow(LOOSE_SAMPLES[name]))
