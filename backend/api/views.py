"""API views. Details: specs/plan.md, section 6."""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import InstanceSerializer, JobSerializer, StatusSerializer
from core import watchdog
from core.instance import instance_snapshot
from core.jobs import get_job
from core.status import status_snapshot

ANY_METHOD = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class StatusView(APIView):
    """Configuration status: providers, models, key booleans and settings to fix."""

    def get(self, request):
        return Response(StatusSerializer(status_snapshot()).data)


class InstanceView(APIView):
    """Identifies Card Factory and its home on this port, for the launcher probe."""

    def get(self, request):
        return Response(InstanceSerializer(instance_snapshot()).data)


class HeartbeatView(APIView):
    """A tab is still open: keeps the launcher's watchdog from stopping the application."""

    def post(self, request):
        # Reading the body makes a non-JSON or malformed one answer bad_request before the heartbeat counts.
        request.data
        watchdog.heartbeat()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobView(APIView):
    """A long operation's progress, result or error."""

    def get(self, request, job_id):
        job = get_job(job_id)
        if job is None:
            raise NotFound()
        return Response(JobSerializer(job).data)


@api_view(ANY_METHOD)
def not_found(request, *args, **kwargs):
    """Any unknown `/api/` path, whatever the method."""
    raise NotFound()
