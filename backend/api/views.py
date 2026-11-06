"""API views. Details: specs/plan.md, section 6."""

from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from api.serializers import StatusSerializer
from core.status import status_snapshot

ANY_METHOD = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


class StatusView(APIView):
    """Configuration status: providers, models, key booleans and settings to fix."""

    def get(self, request):
        return Response(StatusSerializer(status_snapshot()).data)


@api_view(ANY_METHOD)
def not_found(request, *args, **kwargs):
    """Any unknown `/api/` path, whatever the method."""
    raise NotFound()
