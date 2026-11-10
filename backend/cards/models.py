"""Models of the cards app: user cards, their immutable versions and usage records.
Details: specs/plan.md, sections 4 and 7.
"""

import uuid

from django.db import models


class Card(models.Model):
    """A user card and the request it came from (see spec RN-26)."""

    class PowerLevel(models.TextChoices):
        CASUAL = "casual"
        MEDIUM = "medium"
        STRONG = "strong"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    current_version = models.ForeignKey(
        "CardVersion", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    idea = models.TextField()
    # A list of color letters; an empty list is a colorless request, not a missing one.
    requested_color_identity = models.JSONField(default=list)
    power_level = models.CharField(max_length=16, choices=PowerLevel.choices)


class ImmutableVersionError(Exception):
    """A stored card version was saved again (see spec RN-25)."""


class CardVersion(models.Model):
    """One immutable, numbered version of a card (see spec RN-25)."""

    class Status(models.TextChoices):
        APPROVED = "approved"
        REJECTED = "rejected"

    class Origin(models.TextChoices):
        GENERATED = "generated"
        REVISED = "revised"

    class PowerIndicator(models.TextChoices):
        TOO_STRONG = "too_strong"
        IN_RANGE = "in_range"
        TOO_WEAK = "too_weak"

    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    origin = models.CharField(max_length=16, choices=Origin.choices, default=Origin.GENERATED)
    name = models.CharField(max_length=200)
    mana_cost = models.CharField(max_length=100, blank=True)
    mana_value = models.PositiveIntegerField()
    type_line = models.CharField(max_length=200)
    rules_text = models.TextField(blank=True)
    power = models.CharField(max_length=16, blank=True)
    toughness = models.CharField(max_length=16, blank=True)
    rarity = models.CharField(max_length=16)
    design_intent = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    # Snapshots of {oracle_id, name, role}: never a link to a catalog row (plan section 7).
    comparables = models.JSONField(default=list)
    power_indicator = models.CharField(max_length=16, choices=PowerIndicator.choices)
    power_justification = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    # {status, checks_run, causes, skipped} (plan section 7).
    validation = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["card", "number"], name="cards_version_unique_number"),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableVersionError("A stored card version cannot be changed.")
        super().save(*args, **kwargs)


class UsageRecord(models.Model):
    """Tokens used by one provider call, with or without a card (see spec RN-09)."""

    class Kind(models.TextChoices):
        TEXT = "text"

    class Outcome(models.TextChoices):
        OK = "ok"
        FAILED = "failed"

    card = models.ForeignKey(Card, null=True, blank=True, on_delete=models.SET_NULL, related_name="usage")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    provider = models.CharField(max_length=32)
    model = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=16, choices=Outcome.choices)
    created_at = models.DateTimeField(auto_now_add=True)
