"""API routes under `/api/`. Details: specs/plan.md, section 6."""

from django.urls import path, re_path

from api import views

urlpatterns = [
    path("status", views.StatusView.as_view(), name="status"),
    # Last: an unknown API path answers 404 in the envelope, never an HTML page.
    re_path(r"", views.not_found),
]
