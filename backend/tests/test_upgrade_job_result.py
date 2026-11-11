"""Upgrade of the job table from core migration 0001 to 0002 (task T117, spec RN-42).

Core migration 0002 changes `Job.result` from a card id to a JSON value. A data
folder written by an older version holds build jobs created under 0001; after the
upgrade the jobs must read through the ORM without error. Every value is fictional.
"""

import uuid

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = [("core", "0001_initial")]
AFTER = [("core", "0002_job_result_json")]


def _migrate(targets):
    executor = MigrationExecutor(connection)
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.fixture
def restore_latest():
    yield
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


def test_t117_rn42_old_build_jobs_read_through_the_orm_after_the_upgrade(restore_latest):
    """RN-42: build jobs stored under migration 0001, with no result and with a stored id, survive
    migration 0002 and are read through the ORM with their status, progress and error unchanged."""
    old = _migrate(BEFORE)
    OldJob = old.get_model("core", "Job")
    done = OldJob.objects.create(id=uuid.uuid4(), kind="build", status="done", progress=1.0)
    failed = OldJob.objects.create(
        id=uuid.uuid4(),
        kind="build",
        status="failed",
        progress=0.4,
        error={"error": {"code": "internal", "message": "A fictional failure.", "setting": None, "fields": None}},
    )
    with_id = OldJob.objects.create(id=uuid.uuid4(), kind="generate", status="done", progress=1.0, result=uuid.uuid4())

    _migrate(AFTER)

    from core.models import Job

    stored = {job.pk: job for job in Job.objects.all()}
    assert set(stored) == {done.pk, failed.pk, with_id.pk}
    assert (stored[done.pk].kind, stored[done.pk].status, stored[done.pk].progress) == ("build", "done", 1.0)
    assert stored[done.pk].result is None
    assert stored[failed.pk].status == "failed"
    assert stored[failed.pk].error["error"]["code"] == "internal"
    assert stored[with_id.pk].result is None or isinstance(stored[with_id.pk].result, (dict, str))


def test_t117_rn42_an_upgraded_job_table_accepts_a_json_result(restore_latest):
    """RN-42: after the upgrade, a generation job stores and reads back its JSON result."""
    _migrate(BEFORE)
    _migrate(AFTER)

    from core.models import Job

    result = {"card": str(uuid.uuid4()), "revision_failure": None}
    job = Job.objects.create(kind="generate", status="done", progress=1.0, result=result)

    assert Job.objects.get(pk=job.pk).result == result
