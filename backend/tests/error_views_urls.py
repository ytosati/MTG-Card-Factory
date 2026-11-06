"""Test-only URL configuration: the real routes plus API views that raise on purpose.

Used with `@pytest.mark.urls("tests.error_views_urls")` to check how the API
maps exceptions to the error envelope (plan section 6). The test routes come
first, because the real `/api/` routes end with a catch-all 404.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import path
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from cardfactory import urls as real_urls
from tests.config_files import FAKE_TEXT_KEY


class _RaisingView(APIView):
    """An API view with no authentication or permission that raises `error()` on GET."""

    authentication_classes = []
    permission_classes = []
    error = None

    def get(self, request):
        raise self.error()


def _view(factory):
    return _RaisingView.as_view(error=factory)


urlpatterns = [
    path("api/test-errors/runtime", _view(lambda: RuntimeError(f"boom {FAKE_TEXT_KEY}"))),
    path("api/test-errors/api-exception", _view(lambda: APIException(f"detail {FAKE_TEXT_KEY}"))),
    path("api/test-errors/not-found", _view(lambda: Http404(f"missing {FAKE_TEXT_KEY}"))),
    path("api/test-errors/permission-denied", _view(lambda: PermissionDenied(f"denied {FAKE_TEXT_KEY}"))),
    *real_urls.urlpatterns,
]

# Keep the project's error handlers, when it defines any.
for _name in ("handler400", "handler403", "handler404", "handler500"):
    if hasattr(real_urls, _name):
        globals()[_name] = getattr(real_urls, _name)
