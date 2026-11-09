"""Source registry and catalog version.
Details: specs/plan.md, section 7 ("Catalog version").
"""

from dataclasses import dataclass

from catalog.models import SourceRecord

CATALOG_VERSION = 1


@dataclass(frozen=True)
class Source:
    """One entry of the registry; `name` is a SourceRecord.source value."""

    name: str


SOURCES = (Source(name=SourceRecord.Source.SCRYFALL_ORACLE),)
