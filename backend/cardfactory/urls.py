"""Root URL configuration. Details: specs/plan.md, sections 6 and 9.5."""

from django.urls import include, path, re_path

from api import frontend

urlpatterns = [
    path("api/", include("api.urls")),
    re_path(r"^assets(?:/(?P<relative>[\s\S]*))?$", frontend.asset),
    # Not `api` itself: it keeps the slash redirect to the API's 404 envelope.
    re_path(r"^(?!api/?$)", frontend.index),
]
