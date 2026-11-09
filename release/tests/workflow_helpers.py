"""Test helpers for the CI workflow: a standard-library reader for block-style YAML and job commands.

The reader raises WorkflowSyntaxError for the errors it knows, such as tabs, stray indentation and duplicate keys.
"""

import posixpath
import re
import shlex

import pytest

from repo_check_helpers import REPO_ROOT

WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "tests.yml"
WORKFLOW_NAME = WORKFLOW_PATH.relative_to(REPO_ROOT).as_posix()


class WorkflowSyntaxError(ValueError):
    """The text is not in the block-style YAML subset the reader accepts."""


_KEY_PATTERN = re.compile(r"""^("[^"]*"|'[^']*'|[^\s"'#:\-\[\]{}&*!|>%@`][^:]*?)\s*:(?:\s+(.*))?$""")
_BLOCK_SCALAR = re.compile(r"^[|>][+-]?$")


def _strip_comment(text):
    """Remove a trailing comment that sits outside quotes."""
    quote = None
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'" and (index == 0 or text[index - 1] in " [,"):
            quote = char
        elif char == "#" and (index == 0 or text[index - 1] in " \t"):
            return text[:index].rstrip()
    return text.rstrip()


def _scalar(text, line_number):
    text = _strip_comment(text).strip()
    if text[:1] in "&*!{":
        raise WorkflowSyntaxError(f"line {line_number}: unsupported construct {text!r}")
    if text.startswith("["):
        if not text.endswith("]"):
            raise WorkflowSyntaxError(f"line {line_number}: unclosed flow sequence")
        inner = text[1:-1].strip()
        return [_scalar(part, line_number) for part in inner.split(",")] if inner else []
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    if text[:1] in "\"'":
        raise WorkflowSyntaxError(f"line {line_number}: unclosed quote")
    if ": " in text or text.endswith(":"):
        raise WorkflowSyntaxError(f"line {line_number}: plain value {text!r} holds ': ', which needs quotes")
    return text


def _indent(raw):
    return len(raw) - len(raw.lstrip(" "))


class _Reader:
    def __init__(self, text):
        for number, raw in enumerate(text.splitlines(), start=1):
            leading = raw[: len(raw) - len(raw.lstrip(" \t"))]
            if "\t" in leading:
                raise WorkflowSyntaxError(f"line {number}: indentation uses a tab")
        self.lines = text.splitlines()
        self.index = 0

    def _peek(self):
        while self.index < len(self.lines):
            stripped = self.lines[self.index].strip()
            if stripped and not stripped.startswith("#") and stripped != "---":
                raw = self.lines[self.index]
                return _indent(raw), raw.strip()
            self.index += 1
        return None

    def read(self):
        first = self._peek()
        if first is None:
            raise WorkflowSyntaxError("the workflow is empty")
        if first[0] != 0:
            raise WorkflowSyntaxError("the first key is indented")
        node = self._node(0)
        if self._peek() is not None:
            raise WorkflowSyntaxError(f"line {self.index + 1}: unexpected indentation")
        return node

    def _node(self, indent):
        _, content = self._peek()
        if content == "-" or content.startswith("- "):
            return self._sequence(indent)
        return self._mapping(indent)

    def _mapping(self, indent):
        result = {}
        while True:
            peeked = self._peek()
            if peeked is None or peeked[0] < indent:
                return result
            line_number = self.index + 1
            if peeked[0] > indent:
                raise WorkflowSyntaxError(f"line {line_number}: unexpected indentation")
            content = peeked[1]
            if content == "-" or content.startswith("- "):
                if result:
                    raise WorkflowSyntaxError(f"line {line_number}: list item inside a mapping")
                return result
            match = _KEY_PATTERN.match(_strip_comment(content))
            if not match:
                raise WorkflowSyntaxError(f"line {line_number}: expected 'key: value', got {content!r}")
            key = match.group(1)
            if key[:1] in "\"'":
                key = key[1:-1]
            if key in result:
                raise WorkflowSyntaxError(f"line {line_number}: duplicate key {key!r}")
            self.index += 1
            result[key] = self._value(match.group(2) or "", indent, line_number)

    def _value(self, rest, indent, line_number):
        rest = _strip_comment(rest).strip()
        if _BLOCK_SCALAR.match(rest):
            return self._block_scalar(indent, folded=rest.startswith(">"))
        if rest:
            return _scalar(rest, line_number)
        peeked = self._peek()
        if peeked is None:
            return None
        child_indent, content = peeked
        is_item = content == "-" or content.startswith("- ")
        if child_indent > indent or (child_indent == indent and is_item):
            return self._node(child_indent)
        return None

    def _sequence(self, indent):
        items = []
        while True:
            peeked = self._peek()
            if peeked is None or peeked[0] < indent:
                return items
            line_number = self.index + 1
            child_indent, content = peeked
            if child_indent > indent:
                raise WorkflowSyntaxError(f"line {line_number}: unexpected indentation")
            if not (content == "-" or content.startswith("- ")):
                return items
            after = content[1:]
            item_text = after.lstrip(" ")
            if not item_text:
                self.index += 1
                items.append(self._value("", indent, line_number))
                continue
            column = indent + 1 + (len(after) - len(item_text))
            if _KEY_PATTERN.match(_strip_comment(item_text)):
                self.lines[self.index] = " " * column + item_text
                items.append(self._mapping(column))
            else:
                self.index += 1
                items.append(_scalar(item_text, line_number))

    def _block_scalar(self, parent_indent, folded):
        collected = []
        while self.index < len(self.lines):
            raw = self.lines[self.index]
            if raw.strip() and _indent(raw) <= parent_indent:
                break
            collected.append(raw)
            self.index += 1
        while collected and not collected[-1].strip():
            collected.pop()
        body = [line for line in collected if line.strip()]
        if not body:
            return ""
        content_indent = min(_indent(line) for line in body)
        lines = [line[content_indent:] for line in collected]
        return " ".join(lines) if folded else "\n".join(lines)


def parse_workflow(text):
    """Read workflow text into dicts, lists and strings, or raise WorkflowSyntaxError."""
    return _Reader(text).read()


def read_workflow_text():
    if not WORKFLOW_PATH.is_file():
        pytest.fail(f"Missing CI workflow: {WORKFLOW_NAME}")
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def load_workflow():
    text = read_workflow_text()
    try:
        return parse_workflow(text)
    except WorkflowSyntaxError as error:
        pytest.fail(f"{WORKFLOW_NAME} does not pass the syntax check: {error}")


def trigger_names(workflow):
    triggers = workflow.get("on")
    if isinstance(triggers, str):
        return {triggers: None}
    if isinstance(triggers, list):
        return {name: None for name in triggers}
    if isinstance(triggers, dict):
        return triggers
    return {}


def jobs(workflow):
    value = workflow.get("jobs")
    return value if isinstance(value, dict) else {}


def steps(job):
    value = job.get("steps") if isinstance(job, dict) else None
    return value if isinstance(value, list) else []


def normalize_dir(path):
    """A folder relative to the repository root, '.' for the root itself."""
    path = str(path).strip().replace("\\", "/")
    path = re.sub(r"^\$\{\{\s*github\.workspace\s*\}\}/?", "", path)
    path = re.sub(r"^\$GITHUB_WORKSPACE/?", "", path)
    return posixpath.normpath(path or ".")


def _default_dir(node):
    defaults = node.get("defaults") if isinstance(node, dict) else None
    run = defaults.get("run") if isinstance(defaults, dict) else None
    folder = run.get("working-directory") if isinstance(run, dict) else None
    return folder


def _python_module_prefix(tokens):
    if len(tokens) >= 3 and re.fullmatch(r"python(3(\.\d+)?)?(\.exe)?", tokens[0]) and tokens[1] == "-m":
        return tokens[2:]
    return tokens


def job_commands(workflow, job):
    """Every shell command of a job, in order, as (position, folder, tokens)."""
    base = _default_dir(job) or _default_dir(workflow) or "."
    commands = []
    for step_index, step in enumerate(steps(job)):
        if not isinstance(step, dict) or not isinstance(step.get("run"), str):
            continue
        cwd = normalize_dir(step.get("working-directory") or base)
        script = re.sub(r"\\\n\s*", " ", step["run"])
        for line in script.splitlines():
            for part in re.split(r"&&|;|\|\|", _strip_comment(line)):
                part = part.strip()
                if not part:
                    continue
                try:
                    tokens = shlex.split(part)
                except ValueError:
                    tokens = part.split()
                if tokens and tokens[0] == "cd" and len(tokens) >= 2:
                    cwd = normalize_dir(posixpath.join(cwd, normalize_dir(tokens[1])))
                    continue
                commands.append(((step_index, len(commands)), cwd, _python_module_prefix(tokens)))
    return commands


def is_suite_command(cwd, tokens):
    return any(
        matcher(cwd, tokens)
        for matcher in (is_backend_pytest, is_launcher_release_pytest, is_frontend_test, is_type_check)
    )


def _is_on(value):
    return value is not None and str(value).strip().lower() not in ("false", "")


def suite_failure_problems(workflow):
    """Ways a failing suite could leave its job green: tolerated errors, skipped steps, chained commands."""
    problems = []
    for job_id, job in jobs(workflow).items():
        commands = job_commands(workflow, job)
        for step_index, step in enumerate(steps(job)):
            step_commands = [(cwd, tokens) for (index, _), cwd, tokens in commands if index == step_index]
            if not any(is_suite_command(cwd, tokens) for cwd, tokens in step_commands):
                continue
            where = f"job {job_id}, step {step_index + 1}"
            if _is_on(job.get("continue-on-error")):
                problems.append(f"{where}: the job sets continue-on-error")
            if "if" in job:
                problems.append(f"{where}: the job has an if condition")
            if _is_on(step.get("continue-on-error")):
                problems.append(f"{where}: the step sets continue-on-error")
            if "if" in step:
                problems.append(f"{where}: the step has an if condition")
            script = step["run"].strip()
            if len(step_commands) != 1 or "\n" in script or re.search(r"&&|\|\||;|\bexit\b", script):
                problems.append(f"{where}: the run script holds more than the suite command: {script!r}")
    return problems


def is_backend_pytest(cwd, tokens):
    return cwd == "backend" and tokens[:1] == ["pytest"] and "-q" in tokens


def is_launcher_release_pytest(cwd, tokens):
    return cwd == "." and tokens[:1] == ["pytest"] and "launcher" in tokens and "release" in tokens


def is_frontend_test(cwd, tokens):
    return cwd == "frontend" and (tokens[:3] == ["npm", "run", "test"] or tokens[:2] == ["npm", "test"])


def is_type_check(cwd, tokens):
    return cwd == "frontend" and tokens[:3] == ["npx", "tsc", "-b"]


def is_npm_ci(cwd, tokens):
    return cwd == "frontend" and tokens[:2] == ["npm", "ci"]


def pip_requirement_files(cwd, tokens):
    """The requirement files a pip install reads, relative to the repository root."""
    if tokens[:2] != ["pip", "install"]:
        return None
    files = []
    for index, token in enumerate(tokens):
        if token in ("-r", "--requirement") and index + 1 < len(tokens):
            files.append(normalize_dir(posixpath.join(cwd, tokens[index + 1])))
        elif token.startswith("--requirement="):
            files.append(normalize_dir(posixpath.join(cwd, token.split("=", 1)[1])))
    return files


def pip_extra_packages(tokens):
    """Packages named on a pip install line besides requirement files and pip itself."""
    extra = []
    skip_next = False
    for token in tokens[2:]:
        if skip_next:
            skip_next = False
            continue
        if token in ("-r", "--requirement", "-c", "--constraint"):
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        if token.lower() != "pip":
            extra.append(token)
    return extra


def walk(node):
    """Yield every mapping in the parsed workflow."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)
