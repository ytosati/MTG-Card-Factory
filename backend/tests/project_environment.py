"""Test helper: the environment variables that carry project configuration.

Single source for the variables the test session and the settings probes clear.
"""

PROJECT_VARIABLE_PREFIXES = ("CARDFACTORY_", "LLM_", "IMAGE_", "DJANGO_")
PROJECT_VARIABLE_NAMES = frozenset({"APP_PORT"})


def is_project_variable(name):
    """True when `name` is a project setting that must not leak into tests."""
    upper = name.upper()
    return upper.startswith(PROJECT_VARIABLE_PREFIXES) or upper in PROJECT_VARIABLE_NAMES
