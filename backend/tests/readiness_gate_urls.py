"""Test-only URL configuration: the real routes plus one API view that keeps the default permissions.

Used with `@pytest.mark.urls("tests.readiness_gate_urls")` by the readiness gate
tests (task T22, plan section 6): until a later milestone adds an endpoint that
needs the reference database, this probe is the view that shows the default
DRF permission at work. The probe comes first, because the real `/api/` routes
end with a catch-all 404.
"""

from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView

from cardfactory import urls as real_urls

PROBE_ROUTE = "api/test-gate/probe"


class _GateProbeView(APIView):
    """An API view with the default permission classes, like any endpoint that needs the database."""

    def get(self, request):
        return Response({"probe": "ok"})


urlpatterns = [
    path(PROBE_ROUTE, _GateProbeView.as_view()),
    *real_urls.urlpatterns,
]

for _name in ("handler400", "handler403", "handler404", "handler500"):
    if hasattr(real_urls, _name):
        globals()[_name] = getattr(real_urls, _name)
