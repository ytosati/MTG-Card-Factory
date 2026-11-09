"""API routes under `/api/`. Details: specs/plan.md, section 6."""

from django.urls import path, re_path

from api import views

urlpatterns = [
    path("status", views.StatusView.as_view(), name="status"),
    path("instance", views.InstanceView.as_view(), name="instance"),
    path("heartbeat", views.HeartbeatView.as_view(), name="heartbeat"),
    # Last: an unknown API path answers 404 in the envelope, never an HTML page.
    re_path(r"", views.not_found),
]
