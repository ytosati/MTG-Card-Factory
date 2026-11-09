"""GET /api/jobs/{id} (task T13, spec RN-10, RN-03; plan section 6, Jobs).

The answer is `{id, kind, status, progress, result, error}`, where `error` is
None or the error envelope of plan section 6. A job never carries the text of
an exception. An id with no job, or a path segment that is not a UUID, answers
404 `not_found` in the envelope. Jobs are created with `core.jobs.submit` on an
inline runner (see tests/test_jobs.py for the runner contract).

Requests go through tests.configured_api (temporary home, no network).
"""

import uuid

import pytest

from tests.config_files import FAKE_TEXT_KEY, full_text_settings
from tests.configured_api import assert_error_envelope, configured_api  # noqa: F401 (fixture)
from tests.job_helpers import JOB_FIELDS, envelope_error, inline_runner, job_updates_failing

JOBS_URL = "/api/jobs"
FICTIONAL_CARD_ID = "0b7f3e2a-6c14-4d9b-8a51-2e9c4f7d1b63"

pytestmark = pytest.mark.django_db


class FictionalFailure(Exception):
    """An exception outside any mapped error set."""


def _submit(kind, fn):
    from core.jobs import submit

    with inline_runner():
        return submit(kind, fn)


def _get(api, job_id):
    return api.get(f"{JOBS_URL}/{job_id}")


def _ok_json(response):
    assert response.status_code == 200, response.content[:500]
    assert response["Content-Type"].startswith("application/json")
    return response.json()


def test_t13_rn10_done_job_has_the_plan_shape(configured_api):
    """RN-10 / T13: a done job answers {id, kind, status, progress, result, error} with no error."""
    configured_api.configure(full_text_settings())
    job = _submit("generate", lambda report: FICTIONAL_CARD_ID)

    body = _ok_json(_get(configured_api, job.id))

    assert set(body) == JOB_FIELDS
    assert body["id"] == str(job.id)
    assert body["kind"] == "generate"
    assert body["status"] == "done"
    assert body["result"] == FICTIONAL_CARD_ID
    assert body["error"] is None


def test_t13_rn03_done_build_has_no_result(configured_api):
    """RN-03 / T13: a done build answers result null."""
    configured_api.configure(full_text_settings())
    job = _submit("build", lambda report: None)

    body = _ok_json(_get(configured_api, job.id))

    assert body["kind"] == "build"
    assert body["status"] == "done"
    assert body["result"] is None
    assert body["error"] is None


def test_t13_rn10_failed_job_answers_the_envelope_without_exception_text(configured_api):
    """RN-10 / T13: a failed job answers 200 with the `internal` envelope and none of the exception text."""
    configured_api.configure(full_text_settings())
    detail = f"fictional provider detail OSPREY-5521 {FAKE_TEXT_KEY}"

    def fn(report):
        raise FictionalFailure(detail)

    job = _submit("generate", fn)

    response = _get(configured_api, job.id)
    body = _ok_json(response)

    assert set(body) == JOB_FIELDS
    assert body["status"] == "failed"
    assert body["result"] is None
    assert envelope_error(body["error"])["code"] == "internal"
    text = response.content.decode("utf-8")
    assert "OSPREY-5521" not in text
    assert "FictionalFailure" not in text
    assert FAKE_TEXT_KEY not in text


def test_t13_rn03_orphan_answers_failed(configured_api):
    """RN-03 / RN-10 / T13: a job left running by an earlier process answers failed with an envelope."""
    from core.models import Job

    configured_api.configure(full_text_settings())
    orphan = Job.objects.create(kind="build", status="running")

    body = _ok_json(_get(configured_api, orphan.pk))

    assert body["status"] == "failed"
    envelope_error(body["error"])


# transaction=True: a request runs in autocommit; inside the test's own transaction a failed
# query would poison that transaction and hide the behavior under test.
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("status", ["queued", "running"])
def test_t13_rn10_orphan_answers_failed_when_the_database_is_locked(configured_api, status):
    """RN-10 / T13: when the UPDATE that stores an orphan as failed raises OperationalError
    ("database is locked"), GET /api/jobs/{id} still answers 200 with status failed and an
    envelope, reported in memory; the lock detail never reaches the answer."""
    from core.models import Job

    configured_api.configure(full_text_settings())
    orphan = Job.objects.create(kind="generate", status=status)

    with inline_runner(), job_updates_failing({"failed"}) as refused:
        response = _get(configured_api, orphan.pk)

    assert refused, "The injected failure never triggered."
    body = _ok_json(response)
    assert set(body) == JOB_FIELDS
    assert body["id"] == str(orphan.pk)
    assert body["kind"] == "generate"
    assert body["status"] == "failed"
    assert body["result"] is None
    envelope_error(body["error"])
    assert "database is locked" not in response.content.decode("utf-8")
    assert "OperationalError" not in response.content.decode("utf-8")


def test_t13_unknown_job_id_answers_not_found(configured_api):
    """RN-10 / T13: an id with no job answers 404 `not_found` in the envelope."""
    configured_api.configure(full_text_settings())

    response = _get(configured_api, uuid.uuid4())

    assert_error_envelope(response, 404, "not_found")


@pytest.mark.parametrize(
    "segment",
    [
        "not-a-uuid",
        "0",
        "-1",
        "12345678-1234-1234-1234-12345678901",
        "%20",
        "%E2%9C%93",
        "x" * 5000,
        "1%27%20OR%20%271%27%3D%271",
    ],
    ids=["text", "zero", "negative", "short-uuid", "space", "non-ascii", "huge", "quote"],
)
def test_t13_malformed_job_id_answers_not_found(configured_api, segment):
    """RN-10 / T13: a path segment that is not a UUID answers 404 `not_found` in the envelope, never a 500."""
    configured_api.configure(full_text_settings())

    response = configured_api.get(f"{JOBS_URL}/{segment}")

    assert_error_envelope(response, 404, "not_found")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_t13_job_endpoint_is_read_only(configured_api, method):
    """RN-10 / T13: the job endpoint only answers GET; other methods answer `method_not_allowed`."""
    configured_api.configure(full_text_settings())
    job = _submit("generate", lambda report: FICTIONAL_CARD_ID)

    response = configured_api.request(method, f"{JOBS_URL}/{job.id}", data={})

    assert_error_envelope(response, 405, "method_not_allowed")


def test_t13_job_endpoint_works_without_configuration(configured_api):
    """RN-10 / T13: reading a job needs no provider setting: it answers with no `.env` at all."""
    configured_api.remove_configuration()
    job = _submit("build", lambda report: None)

    assert _ok_json(_get(configured_api, job.id))["status"] == "done"
