"""Models of the catalog app: reference cards and the record of their sources and builds.
Details: specs/plan.md, sections 4 and 7.
"""

from django.db import models


class SourceRecord(models.Model):
    """A downloaded source file: where it came from, when it was published and downloaded."""

    class Source(models.TextChoices):
        SCRYFALL_ORACLE = "scryfall_oracle"

    source = models.CharField(max_length=32, choices=Source.choices)
    url = models.URLField(max_length=500)
    published_at = models.DateTimeField()
    downloaded_at = models.DateTimeField()
    sha256 = models.CharField(max_length=64)
    # Bulk files can exceed a signed 32-bit integer.
    size = models.BigIntegerField()


class BuildRun(models.Model):
    """One completed build; its live state is the build's Job (plan section 4)."""

    catalog_version = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField()


class OracleCard(models.Model):
    """One existing card, identified by its Scryfall oracle id."""

    class CommanderLegality(models.TextChoices):
        LEGAL = "legal"
        BANNED = "banned"
        NOT_LEGAL = "not_legal"

    oracle_id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=300)
    mana_cost = models.CharField(max_length=100, blank=True)
    # Float because a few cards have a fractional mana value.
    cmc = models.FloatField()
    type_line = models.CharField(max_length=300)
    oracle_text = models.TextField(blank=True)
    colors = models.JSONField(default=list, blank=True)
    color_identity = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    power = models.CharField(max_length=16, null=True, blank=True)
    toughness = models.CharField(max_length=16, null=True, blank=True)
    layout = models.CharField(max_length=32)
    faces = models.JSONField(default=list, blank=True)
    commander_legality = models.CharField(max_length=16, choices=CommanderLegality.choices)
    game_changer = models.BooleanField(default=False)
    edhrec_rank = models.PositiveIntegerField(null=True, blank=True)
    roles = models.JSONField(default=list, blank=True)
