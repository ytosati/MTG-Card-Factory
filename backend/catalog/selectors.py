"""Read queries of the catalog app.
Details: specs/plan.md, sections 5 and 7.
"""

from catalog import sources
from catalog.models import BuildRun


def is_ready() -> bool:
    """True when a completed build of the current catalog version exists (see spec RN-03)."""
    return BuildRun.objects.filter(catalog_version=sources.CATALOG_VERSION).exists()
