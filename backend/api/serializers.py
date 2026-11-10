"""Response shapes of the API. Details: specs/plan.md, section 6."""

from rest_framework import serializers

from cards.models import UsageRecord
from catalog.models import SourceRecord
from core.models import Job


class SettingIssueSerializer(serializers.Serializer):
    """A setting to fix or a notice."""

    setting = serializers.CharField()
    code = serializers.CharField()
    message = serializers.CharField()


class SourceSerializer(serializers.ModelSerializer):
    """Origin, publication date and download date of a source (see spec RN-01)."""

    class Meta:
        model = SourceRecord
        fields = ["source", "url", "published_at", "downloaded_at"]


class StatusSerializer(serializers.Serializer):
    """Configuration and database status; keys appear only as booleans (see spec RN-06)."""

    text_provider = serializers.CharField(allow_null=True)
    text_model = serializers.CharField(allow_null=True)
    text_key_configured = serializers.BooleanField()
    image_provider = serializers.CharField(allow_null=True)
    image_model = serializers.CharField(allow_null=True)
    settings = SettingIssueSerializer(many=True)
    next_start_port = serializers.IntegerField(allow_null=True)
    database_ready = serializers.BooleanField()
    sources = SourceSerializer(many=True)


class InstanceSerializer(serializers.Serializer):
    """The instance contract: a newer launcher reads it from an older instance (see spec RN-47)."""

    app = serializers.CharField()
    version = serializers.CharField()
    home = serializers.CharField()


class JobSerializer(serializers.ModelSerializer):
    """A job's progress and outcome; `error` is the error envelope or None."""

    class Meta:
        model = Job
        fields = ["id", "kind", "status", "progress", "result", "error"]


class SetupSerializer(serializers.Serializer):
    """The Setup screen: readiness, build job, sizes in bytes, the listing's failure and settings to fix."""

    database_ready = serializers.BooleanField()
    job = JobSerializer(allow_null=True)
    download_size = serializers.IntegerField(allow_null=True)
    space_needed = serializers.IntegerField(allow_null=True)
    free_space = serializers.IntegerField(allow_null=True)
    listing_error = serializers.JSONField(allow_null=True)
    settings = SettingIssueSerializer(many=True)


class UsageQuerySerializer(serializers.Serializer):
    """The query of `GET /api/usage`: the card whose usage is shown."""

    card = serializers.UUIDField()


class TextUsageSerializer(serializers.ModelSerializer):
    """One text provider call of a card (see spec RN-09)."""

    class Meta:
        model = UsageRecord
        fields = ["provider", "model", "input_tokens", "output_tokens", "outcome", "created_at"]


class UsageSerializer(serializers.Serializer):
    """The usage of a card: its text calls, oldest first."""

    card = serializers.UUIDField()
    text = TextUsageSerializer(many=True)
