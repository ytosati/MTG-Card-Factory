"""Root URL configuration. Details: specs/plan.md, section 6."""

from django.urls import include, path

urlpatterns = [
    path("api/", include("api.urls")),
]
