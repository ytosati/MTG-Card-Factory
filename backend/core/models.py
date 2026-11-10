"""Models of the core app. Details: specs/plan.md, section 4."""

import uuid

from django.db import models


class Job(models.Model):
    """A long operation run in the background: a build, a generation, an adjustment or an art generation."""

    class Kind(models.TextChoices):
        BUILD = "build"
        GENERATE = "generate"
        ADJUST = "adjust"
        ART = "art"

    class Status(models.TextChoices):
        QUEUED = "queued"
        RUNNING = "running"
        DONE = "done"
        FAILED = "failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    progress = models.FloatField(default=0.0)
    # The card id a generation produced; a build has none.
    result = models.UUIDField(null=True, blank=True)
    # The error envelope of plan section 6, never the text of an exception.
    error = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
