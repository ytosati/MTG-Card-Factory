"""Read queries of the core app.
Details: specs/plan.md, sections 5 and 6 (Jobs).
"""

from core.models import Job

ACTIVE_STATUSES = (Job.Status.QUEUED, Job.Status.RUNNING)


def latest_build_job_id():
    """Id of the most recent build job, or None."""
    return Job.objects.filter(kind=Job.Kind.BUILD).order_by("-created_at").values_list("id", flat=True).first()


def active_build_job_ids():
    """Ids of the build jobs stored as queued or running, most recent first."""
    return list(
        Job.objects.filter(kind=Job.Kind.BUILD, status__in=ACTIVE_STATUSES)
        .order_by("-created_at")
        .values_list("id", flat=True)
    )
