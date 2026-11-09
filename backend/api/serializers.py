"""Response shapes of the API. Details: specs/plan.md, section 6."""

from rest_framework import serializers

from core.models import Job


class SettingIssueSerializer(serializers.Serializer):
    """A setting to fix or a notice."""

    setting = serializers.CharField()
    code = serializers.CharField()
    message = serializers.CharField()


class StatusSerializer(serializers.Serializer):
    """Configuration part of the status; keys appear only as booleans (see spec RN-06)."""

    text_provider = serializers.CharField(allow_null=True)
    text_model = serializers.CharField(allow_null=True)
    text_key_configured = serializers.BooleanField()
    image_provider = serializers.CharField(allow_null=True)
    image_model = serializers.CharField(allow_null=True)
    settings = SettingIssueSerializer(many=True)
    next_start_port = serializers.IntegerField(allow_null=True)


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
