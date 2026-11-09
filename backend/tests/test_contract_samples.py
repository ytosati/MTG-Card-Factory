"""API contract samples: `frontend/src/api/contract/samples.ts` (task T126, spec RN-06, CA-06).

Details: specs/plan.md, section 6 (Contract samples). The samples come from the
real endpoints, called through tests.configured_api with a temporary `.env`
(never the repository one), so every response is checked for key values before
it becomes a sample. The frontend client types the samples satisfy live in
`frontend/src/api/types.ts`: `StatusResponse`, `ErrorEnvelope`,
`InstanceResponse` (GET /api/instance, T8), `HeartbeatRequest` (the JSON body
of POST /api/heartbeat, T8), `JobResponse` (GET /api/jobs/{id}, T13, and the 202
answer of POST /api/setup/build, T22) and `SetupResponse` (GET /api/setup, T22).
The heartbeat answers 204 with no body, so its sample is the request body the
endpoint accepted, not a response.

The setup and readiness samples (T22) use the seams of tests.setup_api_helpers:
a fictional data source served by a fake transport, a fake free disk space and
an inline job runner. Each sample starts from a database with no build, no job
and an empty listing cache.

The same run writes `launcher/tests/fixtures/instance.json` from the real
GET /api/instance response (T8), for the launcher probe tests (T74).

To add a sample for a new endpoint, append a SampleRequest to SAMPLE_REQUESTS
and regenerate (see tests.contract_samples).
"""

import json
import re
from dataclasses import dataclass, field

import pytest

from tests.config_files import DEFAULT_PORT, FAKE_IMAGE_KEY, FAKE_TEXT_KEY, env_text, full_text_settings
from tests.configured_api import (
    assert_error_envelope,
    assert_no_key_in_response,
    configured_api,  # noqa: F401 (fixture)
)
from tests.contract_samples import (
    DATETIME_PLACEHOLDER,
    ELAPSED_PLACEHOLDER,
    HOME_PLACEHOLDER,
    SAMPLES_PATH,
    TYPES_MODULE,
    ContractSample,
    Normalizer,
    check_or_update,
    render_samples,
    render_value,
    sample_from_response,
)
from tests.catalog_build_helpers import ORACLE_URI, FakeDataSource, bulk_bytes
from tests.job_helpers import JOB_FIELDS, envelope_error, inline_runner
from tests.settings_probe import REPOSITORY_ROOT
from tests.setup_api_helpers import (
    BUILD_URL,
    PLENTY_OF_SPACE,
    SETUP_URL,
    DuringDownload,
    SetupEnvironment,
    clear_listing_cache,
    own_origin,
)

# The job samples are read from jobs stored in the test database.
pytestmark = pytest.mark.django_db

STATUS_URL = "/api/status"
INSTANCE_URL = "/api/instance"
HEARTBEAT_URL = "/api/heartbeat"
JOBS_URL = "/api/jobs"
UNKNOWN_API_PATH = "/api/no-such-endpoint"
NEXT_START_PORT = 47900

# A configuration saved as UTF-16 with no byte-order mark: it cannot be read as text (spec CA-77).
UNREADABLE_MODEL = "fake-text-model-UTF16-NO-BOM"
UNREADABLE_CONTENT = env_text(
    full_text_settings(model=UNREADABLE_MODEL) | {"APP_PORT": str(DEFAULT_PORT)}
).encode("utf-16-le")

STATUS_TYPE = "StatusResponse"
ERROR_TYPE = "ErrorEnvelope"
INSTANCE_TYPE = "InstanceResponse"
HEARTBEAT_TYPE = "HeartbeatRequest"
JOB_TYPE = "JobResponse"
SETUP_TYPE = "SetupResponse"

OWN_ORIGIN = own_origin(DEFAULT_PORT)

INSTANCE_FIXTURE_PATH = REPOSITORY_ROOT / "launcher" / "tests" / "fixtures" / "instance.json"


@dataclass(frozen=True)
class SampleRequest:
    """How to obtain one sample: the configuration, the request and the expected status code."""

    name: str
    client_type: str
    configuration: dict
    path: str
    status: int = 200
    method: str = "GET"
    running_port: int = DEFAULT_PORT
    secrets: tuple = field(default=())
    # Raw file bytes written instead of `configuration` (another encoding, an unreadable file).
    content: bytes | None = None
    # JSON request body, sent with format="json".
    data: dict | None = None
    # "response": the sample is the response body; "request": the sample is `data`
    # (an endpoint that answers 204 with no body).
    sample: str = "response"
    # Called before the request; returns the path to request instead of `path` (a stored job's URL).
    prepare: object = None
    # Called with the SetupEnvironment before the request, to set the data source or the free space.
    arrange: object = None
    # Called with (api, environment) instead of the plain request; returns the response of the sample.
    obtain: object = None


def _job_path(kind, fn):
    """Run one job inline and return its GET /api/jobs/{id} path."""
    from core.jobs import submit

    with inline_runner():
        job = submit(kind, fn)
    return f"{JOBS_URL}/{job.id}"


def _build_succeeds(report):
    return None


def _build_fails(report):
    raise RuntimeError("fictional build failure detail")


def _post_build(api):
    return api.request("POST", BUILD_URL, data={}, **OWN_ORIGIN)


def _status_after_build(api, environment):
    response = _post_build(api)
    assert response.status_code == 202, response.content[:500]
    return api.get(STATUS_URL)


def _setup_during_build(api, environment):
    watcher = DuringDownload(lambda: api.get(SETUP_URL))
    environment.source.on_request = watcher
    response = _post_build(api)
    assert response.status_code == 202, response.content[:500]
    assert watcher.results, "The bulk file was never requested."
    return watcher.results[0]


def _setup_after_build(api, environment):
    response = _post_build(api)
    assert response.status_code == 202, response.content[:500]
    return api.get(SETUP_URL)


def _cut_bulk(environment):
    environment.use_source(FakeDataSource(cut_bulk=True))


def _listing_unavailable(environment):
    environment.use_source(FakeDataSource(listing_status=503))


def _no_free_space(environment):
    environment.set_free_space(0)


def _unreadable_free_space(environment):
    environment.disk.error = PermissionError(13, "fictional access denied")


SAMPLE_REQUESTS = (
    SampleRequest(
        name="statusFullConfiguration",
        client_type=STATUS_TYPE,
        configuration=full_text_settings()
        | {
            "IMAGE_PROVIDER": "google",
            "IMAGE_API_KEY": FAKE_IMAGE_KEY,
            "IMAGE_MODEL": "fake-image-model-1",
            "APP_PORT": str(DEFAULT_PORT),
        },
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusMissingTextKey",
        client_type=STATUS_TYPE,
        configuration=full_text_settings(key=""),
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusInvalidImageProvider",
        client_type=STATUS_TYPE,
        configuration=full_text_settings()
        | {"IMAGE_PROVIDER": "anthropic", "IMAGE_API_KEY": FAKE_IMAGE_KEY, "IMAGE_MODEL": "fake-image-model-1"},
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusImageKeyIgnored",
        client_type=STATUS_TYPE,
        configuration=full_text_settings(provider="anthropic") | {"IMAGE_API_KEY": FAKE_IMAGE_KEY},
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusImageModelIgnored",
        client_type=STATUS_TYPE,
        configuration=full_text_settings(provider="anthropic") | {"IMAGE_PROVIDER": "", "IMAGE_MODEL": "fake-image-model-1"},
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusNextStartPort",
        client_type=STATUS_TYPE,
        configuration=full_text_settings() | {"APP_PORT": str(NEXT_START_PORT)},
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusUnreadableConfiguration",
        client_type=STATUS_TYPE,
        configuration={},
        content=UNREADABLE_CONTENT,
        path=STATUS_URL,
        running_port=NEXT_START_PORT,
        secrets=(UNREADABLE_MODEL,),
    ),
    SampleRequest(
        name="errorNotFound",
        client_type=ERROR_TYPE,
        configuration=full_text_settings(),
        path=UNKNOWN_API_PATH,
        status=404,
    ),
    SampleRequest(
        name="instance",
        client_type=INSTANCE_TYPE,
        configuration=full_text_settings(),
        path=INSTANCE_URL,
    ),
    SampleRequest(
        name="heartbeatRequest",
        client_type=HEARTBEAT_TYPE,
        configuration=full_text_settings(),
        path=HEARTBEAT_URL,
        method="POST",
        data={},
        status=204,
        sample="request",
    ),
    SampleRequest(
        name="jobBuildDone",
        client_type=JOB_TYPE,
        configuration=full_text_settings(),
        path=JOBS_URL,
        prepare=lambda: _job_path("build", _build_succeeds),
    ),
    SampleRequest(
        name="jobBuildFailed",
        client_type=JOB_TYPE,
        configuration=full_text_settings(),
        path=JOBS_URL,
        prepare=lambda: _job_path("build", _build_fails),
    ),
    SampleRequest(
        name="statusNotReady",
        client_type=STATUS_TYPE,
        configuration=full_text_settings(),
        path=STATUS_URL,
    ),
    SampleRequest(
        name="statusWithSources",
        client_type=STATUS_TYPE,
        configuration=full_text_settings(),
        path=STATUS_URL,
        obtain=_status_after_build,
    ),
    SampleRequest(
        name="setupNotReady",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(),
        path=SETUP_URL,
    ),
    SampleRequest(
        name="setupSettingsToFix",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(key=""),
        path=SETUP_URL,
    ),
    SampleRequest(
        name="setupFreeSpaceUnknown",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(),
        path=SETUP_URL,
        arrange=_unreadable_free_space,
    ),
    SampleRequest(
        name="setupBuilding",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(),
        path=SETUP_URL,
        obtain=_setup_during_build,
    ),
    SampleRequest(
        name="setupBuildFailed",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(),
        path=SETUP_URL,
        arrange=_cut_bulk,
        obtain=_setup_after_build,
    ),
    SampleRequest(
        name="setupListingUnreachable",
        client_type=SETUP_TYPE,
        configuration=full_text_settings(),
        path=SETUP_URL,
        arrange=_listing_unavailable,
    ),
    SampleRequest(
        name="setupBuildAccepted",
        client_type=JOB_TYPE,
        configuration=full_text_settings(),
        path=BUILD_URL,
        method="POST",
        status=202,
        obtain=lambda api, environment: _post_build(api),
    ),
    SampleRequest(
        name="setupBuildRefusedForSpace",
        client_type=ERROR_TYPE,
        configuration=full_text_settings(),
        path=BUILD_URL,
        method="POST",
        status=507,
        arrange=_no_free_space,
        obtain=lambda api, environment: _post_build(api),
    ),
)


@pytest.fixture(autouse=True)
def setup_seams(request, monkeypatch):
    """For tests that call the API: the fictional data source, plenty of free space and an inline runner (T22)."""
    if "configured_api" not in request.fixturenames:
        yield None
        return
    api = request.getfixturevalue("configured_api")
    with inline_runner():
        api.setup_environment = SetupEnvironment(monkeypatch)
        yield api.setup_environment
    clear_listing_cache()


def _fresh_catalog(environment):
    """No build, no job, an empty listing cache, the default data source and plenty of free space."""
    from catalog.models import BuildRun, OracleCard, SourceRecord
    from core.models import Job

    BuildRun.objects.all().delete()
    SourceRecord.objects.all().delete()
    OracleCard.objects.all().delete()
    Job.objects.all().delete()
    environment.use_source(FakeDataSource())
    environment.set_free_space(PLENTY_OF_SPACE)
    environment.disk.error = None
    clear_listing_cache()


def _call(api, request):
    api.set_running_port(request.running_port)
    if request.content is not None:
        api.configure_bytes(request.content, secrets=request.secrets)
    else:
        api.configure(request.configuration, secrets=request.secrets)
    environment = api.setup_environment
    _fresh_catalog(environment)
    if request.arrange is not None:
        request.arrange(environment)
    path = request.prepare() if request.prepare is not None else request.path
    # configured_api fails here when a key value appears anywhere in the response.
    if request.obtain is not None:
        response = request.obtain(api, environment)
    else:
        response = api.request(request.method, path, data=request.data)
    assert response.status_code == request.status, (request.name, response.status_code, response.content[:500])
    return response


def _collect(api, requests=SAMPLE_REQUESTS):
    samples = []
    for request in requests:
        response = _call(api, request)
        if request.sample == "request":
            assert response.content == b"", (request.name, response.content[:500])
            samples.append(ContractSample(request.name, request.client_type, Normalizer(api.home)(request.data)))
        else:
            samples.append(sample_from_response(request.name, request.client_type, response, home=api.home))
    return samples


def _by_name(samples):
    return {sample.name: sample.body for sample in samples}


# --- The committed file matches the API ---


def test_t126_rn06_samples_file_matches_the_api(configured_api):
    """RN-06 / CA-06 / T126: samples.ts is exactly the text generated from the current responses
    (with CARDFACTORY_UPDATE_CONTRACT=1 outside CI, a different file is rewritten and the test fails once)."""
    text = render_samples(_collect(configured_api))

    check_or_update(text)


def test_t126_ca06_no_sample_contains_a_key_value(configured_api):
    """CA-06 / RN-06 / T126: neither the generated text nor the committed file holds a key value."""
    text = render_samples(_collect(configured_api))
    committed = SAMPLES_PATH.read_text(encoding="utf-8") if SAMPLES_PATH.exists() else ""

    for secret in configured_api.secrets | {FAKE_TEXT_KEY, FAKE_IMAGE_KEY}:
        for content in (text, committed):
            assert secret not in content, "A key value appears in the contract samples."
            assert json.dumps(secret)[1:-1] not in content, "An escaped key value appears in the contract samples."


def test_t126_rn06_committed_file_uses_lf_and_one_trailing_newline():
    """T126: the committed samples file uses LF line endings and ends with exactly one newline."""
    assert SAMPLES_PATH.exists(), "samples.ts is missing; regenerate it."
    raw = SAMPLES_PATH.read_bytes()

    assert b"\r" not in raw
    assert raw.endswith(b";\n") and not raw.endswith(b"\n\n")


# --- What each sample shows (RN-06 key booleans, the cases the Status screen renders) ---


def test_t126_ca06_status_samples_show_keys_only_as_booleans(configured_api):
    """CA-06 / RN-06 / T126: every status sample reports the text key as a boolean."""
    bodies = _by_name(_collect(configured_api))

    for request in SAMPLE_REQUESTS:
        if request.client_type == STATUS_TYPE:
            assert isinstance(bodies[request.name]["text_key_configured"], bool), request.name


def test_t126_samples_cover_the_named_cases(configured_api):
    """RN-08 / CA-46 / CA-74 / T126: the samples hold the full, missing key, invalid image,
    ignored image key, ignored image model and changed port cases the Status screen renders."""
    bodies = _by_name(_collect(configured_api))

    assert bodies["statusFullConfiguration"]["settings"] == []
    assert bodies["statusFullConfiguration"]["text_key_configured"] is True
    missing = bodies["statusMissingTextKey"]
    assert missing["text_key_configured"] is False
    assert {(entry["setting"], entry["code"]) for entry in missing["settings"]} == {("LLM_API_KEY", "config_invalid")}
    invalid_image = bodies["statusInvalidImageProvider"]
    assert {(entry["setting"], entry["code"]) for entry in invalid_image["settings"]} == {
        ("IMAGE_PROVIDER", "config_invalid")
    }
    ignored = bodies["statusImageKeyIgnored"]
    assert {(entry["setting"], entry["code"]) for entry in ignored["settings"]} == {("IMAGE_API_KEY", "ignored")}
    model_ignored = bodies["statusImageModelIgnored"]
    assert model_ignored["text_provider"] == "anthropic"
    assert model_ignored["image_provider"] is None and model_ignored["image_model"] is None
    assert {(entry["setting"], entry["code"]) for entry in model_ignored["settings"]} == {("IMAGE_MODEL", "ignored")}
    assert bodies["statusNextStartPort"]["next_start_port"] == NEXT_START_PORT
    assert bodies["statusFullConfiguration"]["next_start_port"] is None


def test_t129_ca77_unreadable_configuration_sample_is_the_single_env_item(configured_api):
    """CA-77 / RN-40 / CA-06 / T129: the unreadable-file sample (UTF-16 with no byte-order mark, running port not
    the default) holds the single `.env` item, an empty configuration, no port change and no part of the file."""
    body = _by_name(_collect(configured_api))["statusUnreadableConfiguration"]

    assert [(entry["setting"], entry["code"]) for entry in body["settings"]] == [(".env", "config_invalid")]
    assert "utf-8" in body["settings"][0]["message"].lower()
    assert body["text_provider"] is None and body["text_model"] is None
    assert body["text_key_configured"] is False
    assert body["image_provider"] is None and body["image_model"] is None
    assert body["next_start_port"] is None
    rendered = render_samples([ContractSample("statusUnreadableConfiguration", STATUS_TYPE, body)])
    assert UNREADABLE_MODEL not in rendered
    assert FAKE_TEXT_KEY not in rendered


def test_t126_error_sample_is_the_not_found_envelope(configured_api):
    """T126: the error sample is the envelope of plan section 6 for an unknown /api/ path."""
    request = next(r for r in SAMPLE_REQUESTS if r.client_type == ERROR_TYPE)
    response = _call(configured_api, request)

    error = assert_error_envelope(response, 404, "not_found")

    assert error["setting"] is None and error["fields"] is None


def test_t126_every_sample_name_and_type_is_declared_once():
    """T126: sample names are unique TypeScript identifiers and use only the declared client types."""
    names = [request.name for request in SAMPLE_REQUESTS]

    assert len(names) == len(set(names))
    assert {request.client_type for request in SAMPLE_REQUESTS} == {
        STATUS_TYPE,
        ERROR_TYPE,
        INSTANCE_TYPE,
        HEARTBEAT_TYPE,
        JOB_TYPE,
        SETUP_TYPE,
    }
    assert {request.sample for request in SAMPLE_REQUESTS} <= {"response", "request"}


# --- Instance and heartbeat samples (T8, RN-41, RN-47) ---


def _instance_fixture_text(body):
    return json.dumps(body, indent=2, ensure_ascii=True) + "\n"


def test_t8_rn47_instance_sample_is_the_instance_contract(configured_api):
    """RN-47 / T8: the instance sample is {app: "card-factory", version, home}, with the home normalized
    to the fictional placeholder and the version of a home with no VERSION file."""
    body = _by_name(_collect(configured_api))["instance"]

    assert body == {"app": "card-factory", "version": "0.0.0+unknown", "home": HOME_PLACEHOLDER}


def test_t8_rn41_heartbeat_sample_is_the_empty_json_body():
    """RN-41 / T8: the heartbeat sample is the JSON body `{}` the frontend sends; the endpoint answers 204."""
    request = next(r for r in SAMPLE_REQUESTS if r.client_type == HEARTBEAT_TYPE)

    assert (request.method, request.path, request.status, request.data, request.sample) == (
        "POST",
        HEARTBEAT_URL,
        204,
        {},
        "request",
    )
    rendered = render_samples([ContractSample(request.name, request.client_type, request.data)])
    assert "export const heartbeatRequest = {} satisfies HeartbeatRequest;\n" in rendered


def test_t13_rn10_job_samples_are_a_done_and_a_failed_build(configured_api):
    """RN-10 / RN-03 / T13: the job samples have the plan shape: a done build with no error, and a
    failed build with the `internal` envelope and none of the exception text."""
    bodies = _by_name(_collect(configured_api))

    done = bodies["jobBuildDone"]
    assert set(done) == JOB_FIELDS
    assert (done["kind"], done["status"], done["result"], done["error"]) == ("build", "done", None, None)
    failed = bodies["jobBuildFailed"]
    assert set(failed) == JOB_FIELDS
    assert (failed["kind"], failed["status"], failed["result"]) == ("build", "failed", None)
    assert envelope_error(failed["error"])["code"] == "internal"
    assert "fictional build failure detail" not in json.dumps(failed)


SETUP_FIELDS = {"database_ready", "job", "download_size", "space_needed", "free_space", "listing_error", "settings"}


def test_t22_rn28_setup_samples_cover_the_setup_screen_cases(configured_api):
    """RN-28 / CA-18 / CA-60 / T22: the setup samples hold the not-ready, building, failed-build and
    unreachable-listing answers of GET /api/setup (with and without a setting to fix), the accepted build
    job and the refusal for space."""
    bodies = _by_name(_collect(configured_api))
    size = len(bulk_bytes())

    for name in (
        "setupNotReady",
        "setupSettingsToFix",
        "setupFreeSpaceUnknown",
        "setupBuilding",
        "setupBuildFailed",
        "setupListingUnreachable",
    ):
        assert set(bodies[name]) == SETUP_FIELDS, name
    assert bodies["setupNotReady"]["settings"] == []
    assert {(item["setting"], item["code"]) for item in bodies["setupSettingsToFix"]["settings"]} == {
        ("LLM_API_KEY", "config_invalid")
    }
    not_ready = bodies["setupNotReady"]
    assert (not_ready["database_ready"], not_ready["job"], not_ready["listing_error"]) == (False, None, None)
    assert not_ready["download_size"] == size
    assert not_ready["space_needed"] == size * 3
    assert not_ready["free_space"] == PLENTY_OF_SPACE
    building = bodies["setupBuilding"]
    assert building["database_ready"] is False
    assert building["job"]["kind"] == "build" and building["job"]["status"] == "running"
    assert 0 < building["job"]["progress"] < 1
    failed = bodies["setupBuildFailed"]
    assert failed["database_ready"] is False
    assert failed["job"]["status"] == "failed"
    assert envelope_error(failed["job"]["error"])["code"] == "source_unreachable"
    unreachable = bodies["setupListingUnreachable"]
    assert (unreachable["download_size"], unreachable["space_needed"]) == (None, None)
    assert envelope_error(unreachable["listing_error"])["code"] == "source_unreachable"
    assert bodies["setupFreeSpaceUnknown"]["free_space"] is None
    assert bodies["setupFreeSpaceUnknown"]["download_size"] == size
    accepted = bodies["setupBuildAccepted"]
    assert set(accepted) == JOB_FIELDS and accepted["kind"] == "build"
    assert bodies["setupBuildRefusedForSpace"]["error"]["code"] == "insufficient_space"


def test_t22_ca08_status_samples_show_readiness_and_sources(configured_api):
    """CA-08 / RN-01 / T22: the status samples show the database not ready with no source, and ready with the
    source's origin, publication date and download date."""
    bodies = _by_name(_collect(configured_api))

    not_ready = bodies["statusNotReady"]
    assert (not_ready["database_ready"], not_ready["sources"]) == (False, [])
    ready = bodies["statusWithSources"]
    assert ready["database_ready"] is True
    assert [(entry["source"], entry["url"]) for entry in ready["sources"]] == [("scryfall_oracle", ORACLE_URI)]
    assert ready["sources"][0]["published_at"] == DATETIME_PLACEHOLDER
    assert ready["sources"][0]["downloaded_at"] == DATETIME_PLACEHOLDER


def test_t8_rn47_launcher_instance_fixture_matches_the_api(configured_api):
    """RN-47 / RN-41 / T8: launcher/tests/fixtures/instance.json is the real GET /api/instance response,
    normalized like the samples (with CARDFACTORY_UPDATE_CONTRACT=1 outside CI, it is rewritten)."""
    request = next(r for r in SAMPLE_REQUESTS if r.client_type == INSTANCE_TYPE)
    sample = sample_from_response(request.name, request.client_type, _call(configured_api, request), home=configured_api.home)

    check_or_update(_instance_fixture_text(sample.body), path=INSTANCE_FIXTURE_PATH)


# --- The comparison fails on drift ---


def test_t126_comparison_fails_on_a_changed_response(configured_api):
    """T126: a different response (another model name in the configuration) no longer matches the file."""
    changed = tuple(
        SampleRequest(**(vars(r) | {"configuration": r.configuration | {"LLM_MODEL": "fake-text-model-changed"}}))
        if r.name == "statusFullConfiguration"
        else r
        for r in SAMPLE_REQUESTS
    )
    text = render_samples(_collect(configured_api, changed))

    with pytest.raises(AssertionError, match="no longer match"):
        check_or_update(text, update=False)


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda body: body | {"new_field": True}, id="added-field"),
        pytest.param(lambda body: {k: v for k, v in body.items() if k != "image_model"}, id="removed-field"),
        pytest.param(lambda body: body | {"next_start_port": 0}, id="changed-value"),
    ],
)
def test_t126_comparison_fails_on_a_changed_shape(configured_api, change):
    """T126: an added, removed or changed field in a status response is caught by the comparison."""
    samples = _collect(configured_api)
    samples[0] = ContractSample(samples[0].name, samples[0].client_type, change(samples[0].body))

    with pytest.raises(AssertionError, match="no longer match"):
        check_or_update(render_samples(samples), update=False)


def _one_sample_text(value=1):
    return render_samples([ContractSample("sampleOne", STATUS_TYPE, {"a": [value, 2]})])


def test_t126_update_rewrites_a_different_file_and_fails(tmp_path):
    """T126: with the update switch, a different file is rewritten and the check fails, asking for a review."""
    path = tmp_path / "contract" / "samples.ts"
    path.parent.mkdir()
    path.write_bytes(_one_sample_text(9).encode("utf-8"))
    text = _one_sample_text()

    with pytest.raises(AssertionError, match="was rewritten; review the diff and run again without CARDFACTORY_UPDATE_CONTRACT"):
        check_or_update(text, path=path, update=True, ci=False)

    assert path.read_bytes() == text.encode("utf-8")


def test_t126_update_creates_a_missing_file_and_fails(tmp_path):
    """T126: with the update switch, a missing file is written and the check fails once."""
    path = tmp_path / "contract" / "samples.ts"
    text = _one_sample_text()

    with pytest.raises(AssertionError, match="was rewritten"):
        check_or_update(text, path=path, update=True, ci=False)

    assert path.read_bytes() == text.encode("utf-8")


def test_t126_update_with_identical_content_passes_without_writing(tmp_path):
    """T126: with the update switch, a file already equal to the generated text passes and is left alone."""
    path = tmp_path / "samples.ts"
    text = _one_sample_text()
    path.write_bytes(text.encode("utf-8"))
    before = path.stat().st_mtime_ns

    check_or_update(text, path=path, update=True, ci=False)

    assert path.stat().st_mtime_ns == before


@pytest.mark.parametrize("ci_value", ["true", "1", "yes"])
def test_t126_update_switch_is_ignored_in_ci(tmp_path, monkeypatch, ci_value):
    """T126: when CI is set, the update switch is ignored: the file is only compared and never rewritten."""
    monkeypatch.setenv("CI", ci_value)
    path = tmp_path / "samples.ts"
    stale = _one_sample_text(9)
    path.write_bytes(stale.encode("utf-8"))

    with pytest.raises(AssertionError, match="no longer match"):
        check_or_update(_one_sample_text(), path=path, update=True)

    assert path.read_bytes() == stale.encode("utf-8")


@pytest.mark.parametrize("ci_value", ["", "0", "false"])
def test_t126_update_switch_applies_when_ci_is_off(tmp_path, monkeypatch, ci_value):
    """T126: with CI empty or false, the update switch rewrites the file (and fails once)."""
    monkeypatch.setenv("CI", ci_value)
    path = tmp_path / "samples.ts"
    path.write_bytes(_one_sample_text(9).encode("utf-8"))

    with pytest.raises(AssertionError, match="was rewritten"):
        check_or_update(_one_sample_text(), path=path, update=True)

    assert path.read_bytes() == _one_sample_text().encode("utf-8")


def test_t126_comparison_passes_on_the_same_text_and_fails_on_another(tmp_path):
    """T126: without the update switch the same text passes, any other text fails, and nothing is written."""
    path = tmp_path / "samples.ts"
    text = _one_sample_text()
    path.write_bytes(text.encode("utf-8"))

    check_or_update(text, path=path, update=False)
    with pytest.raises(AssertionError, match="no longer match"):
        check_or_update(_one_sample_text(3), path=path, update=False)

    assert path.read_bytes() == text.encode("utf-8")


def test_t126_comparison_fails_on_crlf_line_endings(tmp_path):
    """T126: a file with CRLF line endings fails with a hint that only the line endings differ."""
    path = tmp_path / "samples.ts"
    text = _one_sample_text()
    path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    with pytest.raises(AssertionError, match="only in line endings; samples.ts uses LF"):
        check_or_update(text, path=path, update=False)


def test_t126_comparison_fails_on_a_missing_file(tmp_path):
    """T126: a missing samples file fails with the way to regenerate it."""
    with pytest.raises(AssertionError, match="CARDFACTORY_UPDATE_CONTRACT=1"):
        check_or_update("text\n", path=tmp_path / "absent.ts", update=False)


# --- Rendering ---


def test_t126_rendering_is_deterministic(configured_api):
    """T126: two runs over the same configuration render the same text, LF only."""
    first = render_samples(_collect(configured_api))
    second = render_samples(_collect(configured_api))

    assert first == second
    assert "\r" not in first


def test_t126_rendered_file_has_header_import_and_one_export_per_sample():
    """T126: header says how to regenerate; one type import; `export const <name> = ... satisfies <Type>;`."""
    samples = [
        ContractSample("statusSample", STATUS_TYPE, {"settings": []}),
        ContractSample("errorSample", ERROR_TYPE, {"error": {"code": "not_found"}}),
    ]

    text = render_samples(samples)

    assert text.startswith("// Generated by ")
    assert "CARDFACTORY_UPDATE_CONTRACT=1" in text
    assert '$env:CARDFACTORY_UPDATE_CONTRACT="1"' in text
    assert text.isascii()
    assert f'import type {{ {ERROR_TYPE}, {STATUS_TYPE} }} from "{TYPES_MODULE}";\n' in text
    assert re.findall(r"^export const (\w+) = ", text, flags=re.M) == ["statusSample", "errorSample"]
    assert "} satisfies StatusResponse;\n" in text
    assert "} satisfies ErrorEnvelope;\n" in text


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param(None, "null", id="null"),
        pytest.param(True, "true", id="true"),
        pytest.param(False, "false", id="false"),
        pytest.param(0, "0", id="zero"),
        pytest.param(-1, "-1", id="negative"),
        pytest.param(1.5, "1.5", id="float"),
        pytest.param("", '""', id="empty-string"),
        pytest.param([], "[]", id="empty-list"),
        pytest.param({}, "{}", id="empty-object"),
        pytest.param({"a": [1]}, "{\n  a: [\n    1,\n  ],\n}", id="nested"),
        pytest.param({"not-an-id": 1, "2x": 2}, '{\n  "not-an-id": 1,\n  "2x": 2,\n}', id="quoted-keys"),
    ],
)
def test_t126_render_value_formats(value, expected):
    """T126: JSON values render as fixed TypeScript text."""
    assert render_value(value) == expected


@pytest.mark.parametrize(
    "text",
    [
        'quote " and backslash \\',
        "line\nbreak\ttab",
        "ção ✓ ギ 🜲 {W/U} {2/B} {G/P}",
        "separators    ",
        "template ${x} `tick` */ <!-- -->",
        "\x00\x01\x7f",
        "x" * 100_000,
    ],
    ids=["quotes", "control-whitespace", "non-ascii-and-hybrid-symbols", "line-separators", "ts-syntax", "nul", "huge"],
)
def test_t126_odd_strings_render_as_safe_ascii_literals(text):
    """T126: any string renders as one ASCII line that reads back as the same string."""
    rendered = render_value(text)

    assert rendered.isascii()
    assert "\n" not in rendered and "\r" not in rendered
    assert rendered.startswith('"') and rendered.endswith('"')
    assert json.loads(rendered) == text


def test_t126_render_rejects_bad_names():
    """T126: duplicate names, names that are not identifiers and bad type names are refused."""
    with pytest.raises(ValueError):
        render_samples([ContractSample("same", STATUS_TYPE, {}), ContractSample("same", STATUS_TYPE, {})])
    with pytest.raises(ValueError):
        render_samples([ContractSample("not-valid", STATUS_TYPE, {})])
    with pytest.raises(ValueError):
        render_samples([ContractSample("ok", "string[]", {})])


# --- Normalization of what varies ---


def test_t126_normalizer_replaces_uuids_consistently():
    """T126: each UUID becomes a fixed placeholder; the same UUID (any case) keeps the same one."""
    first = "3f2b1c4e-9a7d-4e21-8b6a-0c5d7e9f1a2b"
    second = "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"
    body = {"id": first, "items": [{"card": second, "parent": first.upper()}]}

    result = Normalizer()(body)

    assert result["id"] == result["items"][0]["parent"]
    assert result["id"] != result["items"][0]["card"]
    assert first not in json.dumps(result) and second not in json.dumps(result)


@pytest.mark.parametrize(
    "value",
    ["2026-11-06T12:34:56Z", "2026-11-06T12:34:56.123456+00:00", "2026-11-06 12:34:56", "2026-11-06T12:34-03:00"],
)
def test_t126_normalizer_replaces_date_times(value):
    """T126: date-times become a fixed placeholder."""
    assert Normalizer()({"created_at": value}) == {"created_at": DATETIME_PLACEHOLDER}


@pytest.mark.parametrize("name", ["elapsed", "elapsed_ms", "elapsed_seconds", "duration_ms"])
@pytest.mark.parametrize("value", [0, 12, 3.75, -1])
def test_t126_normalizer_replaces_elapsed_times(name, value):
    """T126: elapsed-time fields become a fixed value; other numbers stay."""
    result = Normalizer()({name: value, "next_start_port": 47900, "progress": 0.5})

    assert result == {name: ELAPSED_PLACEHOLDER, "next_start_port": 47900, "progress": 0.5}


def test_t126_normalizer_replaces_the_temporary_home(tmp_path):
    """T126: the temporary home path, with either separator, becomes a fixed fictional path."""
    home = tmp_path / "api-home"
    body = {"home": str(home), "image": str(home / "data" / "a.png").replace("\\", "/")}

    result = Normalizer(home)(body)

    assert result["home"] == HOME_PLACEHOLDER
    assert result["image"].startswith(HOME_PLACEHOLDER)
    assert str(tmp_path) not in json.dumps(result)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        0,
        "",
        "openai",
        "fake-text-model-1",
        "LLM_API_KEY is missing.",
        "2026-11-06",
        "3f2b1c4e-9a7d-4e21-8b6a",
        {"settings": [], "next_start_port": None},
    ],
)
def test_t126_normalizer_leaves_stable_values_alone(value):
    """T126: values that do not vary between runs (plain dates, partial UUIDs, text) are kept."""
    assert Normalizer()(value) == value


def test_t126_sample_from_response_rejects_a_non_json_response():
    """T126: a sample must come from a JSON response."""
    from django.http import HttpResponse

    with pytest.raises(AssertionError):
        sample_from_response("htmlPage", STATUS_TYPE, HttpResponse("<html></html>", content_type="text/html"))


def test_t126_ca06_generated_samples_pass_the_key_check(configured_api):
    """CA-06 / RN-06 / T126: the rendered samples, read as a response, pass the shared key check."""
    from django.http import HttpResponse

    text = render_samples(_collect(configured_api))

    assert_no_key_in_response(HttpResponse(text), configured_api.secrets)
