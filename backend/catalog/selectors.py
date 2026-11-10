"""Read queries of the catalog app.
Details: specs/plan.md, sections 5 and 7.
"""

from catalog import sources
from catalog.models import BuildRun, OracleCard, SourceRecord

TYPOGRAPHIC_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})


def normalize_name(name):
    """A card name as names are compared: case folded, single spaces, no surrounding spaces, straight apostrophes."""
    # Kept equal to validators.name.normalize_name: catalog does not import the validators (plan section 3).
    return " ".join(name.translate(TYPOGRAPHIC_APOSTROPHES).casefold().split())


def is_ready() -> bool:
    """True when a completed build of the current catalog version exists (see spec RN-03)."""
    return BuildRun.objects.filter(catalog_version=sources.CATALOG_VERSION).exists()


def list_sources():
    """The stored source records, with origin, publication date and download date (see spec RN-01)."""
    return list(SourceRecord.objects.order_by("source"))


def existing_card_names():
    """The normalized names of every reference card and of each of its faces (see spec RN-51)."""
    names = set()
    for name, faces in OracleCard.objects.values_list("name", "faces").iterator():
        names.add(normalize_name(name))
        for face in faces or []:
            face_name = face.get("name") if isinstance(face, dict) else None
            if isinstance(face_name, str):
                names.add(normalize_name(face_name))
    names.discard("")
    return frozenset(names)

