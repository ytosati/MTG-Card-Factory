"""Source registry and catalog version.
Details: specs/plan.md, section 7 ("Catalog version").
"""

from dataclasses import dataclass

from catalog.models import SourceRecord

CATALOG_VERSION = 1


@dataclass(frozen=True)
class Source:
    """One entry of the registry; `name` is a SourceRecord.source value, `listing_type`
    the `type` of its file in the data source listing, `allowed_hosts` the only hosts
    it is downloaded from (see spec RN-29)."""

    name: str
    listing_type: str
    allowed_hosts: tuple[str, ...]


SOURCES = (
    Source(
        name=SourceRecord.Source.SCRYFALL_ORACLE,
        listing_type="oracle_cards",
        allowed_hosts=("data.scryfall.io", "api.scryfall.com"),
    ),
)
