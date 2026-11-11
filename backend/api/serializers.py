"""Response shapes of the API. Details: specs/plan.md, section 6."""

from rest_framework import serializers

from cards.models import Card, UsageRecord
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
    """A job's progress and outcome; `result` is the job's JSON result and `error` the error envelope, or None."""

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


# Every color letter of an identity; colorless is the empty list (see spec RN-11).
COLOR_LETTERS = ("W", "U", "B", "R", "G")
IDEA_MAX_LENGTH = 1000


class ColorIdentityField(serializers.ListField):
    """A list of color letters; an invalid item is reported on the field itself, not on its index."""

    child = serializers.ChoiceField(choices=COLOR_LETTERS)
    default_error_messages = {"invalid_choice": "This value is not one of the allowed choices."}

    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as error:
            # Item errors come keyed by index; a list-level error (not a list) is kept as is.
            if isinstance(error.detail, dict):
                self.fail("invalid_choice")
            raise


class GenerationRequestSerializer(serializers.Serializer):
    """The request of `POST /api/generations` (see spec RN-11, CA-26, CA-80); unknown fields are ignored."""

    # Not trimmed, so the idea is stored as sent; the limit counts Unicode characters.
    idea = serializers.CharField(max_length=IDEA_MAX_LENGTH, trim_whitespace=False)
    # An empty list is a colorless request chosen explicitly; null or a missing value is no choice.
    color_identity = ColorIdentityField(allow_empty=True)
    power_level = serializers.ChoiceField(choices=Card.PowerLevel.choices)

    def validate_idea(self, value):
        if not value.strip():
            self.fields["idea"].fail("blank")
        return value


class CardVersionSerializer(serializers.Serializer):
    """The fields of a card version shown by the Result screen (see spec RN-12, RN-13, RN-14, RN-22)."""

    name = serializers.CharField()
    mana_cost = serializers.CharField()
    mana_value = serializers.IntegerField()
    type_line = serializers.CharField()
    rules_text = serializers.CharField()
    power = serializers.CharField()
    toughness = serializers.CharField()
    rarity = serializers.CharField()
    design_intent = serializers.CharField()
    rationale = serializers.CharField()
    comparables = serializers.JSONField()
    power_indicator = serializers.CharField()
    power_justification = serializers.CharField()
    origin = serializers.CharField()
    status = serializers.CharField()
    validation = serializers.JSONField()


class CardUsageSerializer(serializers.Serializer):
    """The usage shown with a card: its text calls, oldest first."""

    text = TextUsageSerializer(many=True)


class CardSerializer(serializers.Serializer):
    """A card with its current version and its usage (see spec RN-26, RN-09)."""

    id = serializers.UUIDField()
    current_version = CardVersionSerializer(allow_null=True)
    usage = CardUsageSerializer()
