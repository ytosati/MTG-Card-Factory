"""API views. Details: specs/plan.md, section 6."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from api.exceptions import CARD_NOT_FOUND_MESSAGE, CODE_NOT_FOUND
from api.serializers import (
    InstanceSerializer,
    JobSerializer,
    SetupSerializer,
    StatusSerializer,
    UsageQuerySerializer,
    UsageSerializer,
)
from cards.selectors import get_card, usage_for
from catalog.setup import request_build, setup_snapshot
from core import watchdog
from core.errors import MappedError
from core.instance import instance_snapshot
from core.jobs import get_job
from core.status import status_snapshot

ANY_METHOD = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class StatusView(APIView):
    """Configuration status, database readiness and sources."""

    permission_classes = []

    def get(self, request):
        return Response(StatusSerializer(status_snapshot()).data)


class InstanceView(APIView):
    """Identifies Card Factory and its home on this port, for the launcher probe."""

    permission_classes = []

    def get(self, request):
        return Response(InstanceSerializer(instance_snapshot()).data)


class HeartbeatView(APIView):
    """A tab is still open: keeps the launcher's watchdog from stopping the application."""

    permission_classes = []

    def post(self, request):
        # Reading the body makes a non-JSON or malformed one answer bad_request before the heartbeat counts.
        request.data
        watchdog.heartbeat()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobView(APIView):
    """A long operation's progress, result or error."""

    permission_classes = []

    def get(self, request, job_id):
        job = get_job(job_id)
        if job is None:
            raise NotFound()
        return Response(JobSerializer(job).data)


class SetupView(APIView):
    """Build state, download size and free space for the Setup screen (see spec RN-28)."""

    permission_classes = []

    def get(self, request):
        return Response(SetupSerializer(setup_snapshot()).data)


class SetupBuildView(APIView):
    """Starts the reference database build, or returns the one that runs."""

    permission_classes = []

    def post(self, request):
        # Reading the body makes a non-JSON or malformed one answer bad_request before a build starts.
        request.data
        return Response(JobSerializer(request_build()).data, status=status.HTTP_202_ACCEPTED)


class UsageView(APIView):
    """The text usage records of a card (see spec RN-09)."""

    def get(self, request):
        query = UsageQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        card = get_card(query.validated_data["card"])
        if card is None:
            raise MappedError(CODE_NOT_FOUND, CARD_NOT_FOUND_MESSAGE)
        return Response(UsageSerializer({"card": card.pk, "text": usage_for(card)}).data)


@api_view(ANY_METHOD)
@permission_classes([])
def not_found(request, *args, **kwargs):
    """Any unknown `/api/` path, whatever the method."""
    raise NotFound()
