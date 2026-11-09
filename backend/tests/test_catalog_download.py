"""Source downloader (task T15, spec RN-01, RN-03, RN-28, RN-29, CA-07).

Details: specs/plan.md, sections 7 (data folder, all-or-nothing build, phase 1:
download to `data/downloads/`, check size and checksum, resume with `If-Range`)
and 10 (descriptive User-Agent and Accept header); error codes in section 6.

API under test:

    catalog.download.DOWNLOAD_ATTEMPTS
        3: attempts in all for one download (RN-28).

    catalog.download.download_file(url, filename, *, expected_size=None,
                                   transport, sleep, open_file=open)
        Downloads `url` to `data_dir() / "downloads" / filename` and returns a
        result with `.path` (the file), `.size` (bytes) and `.sha256` (hex
        digest of the whole file), the values recorded in the source record.
        `expected_size` is the size stated by the data source's listing; when it
        is None, the `Content-Length` of a full response is the expected size.
        Between failed attempts it calls `sleep(seconds)` with a short pause
        that grows from one attempt to the next.

    transport(url, headers) -> response
        The seam over urllib. `headers` is a dict of request headers. The
        response has `.status` (int, any HTTP status, errors included),
        `.headers` (case-insensitive `.get(name)`, as urllib's HTTPMessage),
        `.chunks` (an iterable of bytes that may raise OSError mid-stream) and
        `.close()`. A network failure raises an OSError (urllib.error.URLError,
        TimeoutError, ConnectionResetError...).

    open_file(path, mode) -> binary file object
        The seam over the writer; `open` by default.

    catalog.download.DownloadError
        Raised when every attempt failed. `.code` is an error code of plan
        section 6: `source_unreachable` (no network, source failure, size
        mismatch) or `insufficient_space` (disk full, not retried); its message
        states the cause.

    catalog.download.read_listing(*, transport, sleep)
        The data source's download listing; see the section "download listing".

No test touches the network: every response is written by hand below.
"""

import datetime
import errno
import hashlib
import http.client
import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from core.paths import data_dir

URL = "https://data.scryfall.io/oracle-cards/fictional-oracle-cards-20261108.json"
FILENAME = "fictional-oracle-cards.json"
BODY = b'[{"name": "Gloomfen Archivist"}, {"name": "Brasslung Herald"}]\n' * 8
NEW_BODY = b'[{"name": "Tidewrit Cartographer"}]\n' * 9
ETAG = '"fictional-etag-1"'
NEW_ETAG = '"fictional-etag-2"'
LAST_MODIFIED = "Tue, 03 Nov 2026 09:00:00 GMT"
CHUNK = 16


# ---------------------------------------------------------------- fakes


def _headers(values):
    message = http.client.HTTPMessage()
    for name, value in values.items():
        message[name] = value
    return message


class FakeResponse:
    def __init__(self, status, headers=None, body=b"", cut_after=None, chunk=CHUNK):
        self.status = status
        self.headers = _headers(headers or {})
        self._body = body
        self._cut_after = cut_after
        self._chunk = chunk
        self.closed = False

    @property
    def chunks(self):
        return self._generate()

    def _generate(self):
        limit = len(self._body) if self._cut_after is None else self._cut_after
        for start in range(0, limit, self._chunk):
            yield self._body[start : min(start + self._chunk, limit)]
        if self._cut_after is not None:
            raise ConnectionResetError(errno.ECONNRESET, "Connection reset by peer")

    def close(self):
        self.closed = True


class FakeServer:
    """A hand-written data source that honours `Range` with `If-Range` like an HTTP server.

    `cuts` lists, per request, how many bytes are sent before the connection
    drops (None sends everything). `script` overrides a request with a fixed
    response or exception.
    """

    def __init__(
        self,
        body=BODY,
        etag=ETAG,
        last_modified=None,
        accepts_ranges=True,
        cuts=(),
        script=None,
        content_length=True,
    ):
        self.body = body
        self.etag = etag
        self.last_modified = last_modified
        self.accepts_ranges = accepts_ranges
        self.cuts = list(cuts)
        self.script = dict(script or {})
        self.content_length = content_length
        self.requests = []

    def _validators(self):
        values = {}
        if self.etag is not None:
            values["ETag"] = self.etag
        if self.last_modified is not None:
            values["Last-Modified"] = self.last_modified
        return values

    def __call__(self, url, headers):
        index = len(self.requests)
        lowered = {str(name).lower(): value for name, value in dict(headers).items()}
        self.requests.append((url, lowered))
        cut = self.cuts[index] if index < len(self.cuts) else None
        if index in self.script:
            step = self.script[index]
            if isinstance(step, BaseException):
                raise step
            return step

        range_value = lowered.get("range")
        if_range = lowered.get("if-range")
        validators = self._validators()
        if (
            range_value
            and self.accepts_ranges
            and if_range is not None
            and if_range in (self.etag, self.last_modified)
        ):
            start = int(range_value.split("=", 1)[1].split("-", 1)[0])
            rest = self.body[start:]
            response_headers = {
                **validators,
                "Content-Range": f"bytes {start}-{len(self.body) - 1}/{len(self.body)}",
                "Content-Length": str(len(rest)),
            }
            return FakeResponse(206, response_headers, rest, cut_after=cut)

        response_headers = dict(validators)
        if self.accepts_ranges:
            response_headers["Accept-Ranges"] = "bytes"
        if self.content_length:
            response_headers["Content-Length"] = str(len(self.body))
        return FakeResponse(200, response_headers, self.body, cut_after=cut)


class FakeSleep:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


class DiskFullFile:
    """A real binary file whose writes fail as on a full disk."""

    def __init__(self, handle):
        self._handle = handle

    def write(self, data):
        raise OSError(errno.ENOSPC, "No space left on device")

    def __getattr__(self, name):
        return getattr(self._handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._handle.close()
        return False


def disk_full_open(path, mode="rb", *args, **kwargs):
    handle = open(path, mode, *args, **kwargs)
    if any(flag in mode for flag in "wax+"):
        return DiskFullFile(handle)
    return handle


# ---------------------------------------------------------------- fixtures


@pytest.fixture
def home(monkeypatch, tmp_path):
    """A temporary application home with an empty data folder."""
    folder = tmp_path / "home"
    (folder / "data").mkdir(parents=True)
    monkeypatch.setenv("CARDFACTORY_HOME", str(folder))
    return folder


@pytest.fixture
def download():
    from catalog import download as module

    return module


def _destination():
    return data_dir() / "downloads" / FILENAME


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _range_requests(server):
    return [headers for _, headers in server.requests if "range" in headers]


def _assert_every_range_has_if_range(server):
    """RN-03, plan section 7: a range is only asked for together with If-Range."""
    for headers in _range_requests(server):
        assert headers.get("if-range"), f"Range sent without If-Range: {headers}"


# ---------------------------------------------------------------- success


def test_t15_rn28_download_attempts_constant_is_three(download):
    """RN-28: a failed download is tried up to three attempts in all."""
    assert download.DOWNLOAD_ATTEMPTS == 3


def test_t15_rn01_success_writes_file_under_data_downloads_with_sha256_and_size(home, download):
    """RN-01, RN-03: the source is saved in data/downloads/ with its SHA-256 and size."""
    server = FakeServer()
    sleep = FakeSleep()

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep)

    assert result.path == _destination()
    assert _destination().read_bytes() == BODY
    assert result.size == len(BODY)
    assert result.sha256 == _sha(BODY)
    assert len(server.requests) == 1
    assert server.requests[0][0] == URL
    assert sleep.calls == []


def test_t15_rn01_success_without_listing_size_uses_content_length(home, download):
    """RN-03: with no size from the listing, the Content-Length is the expected size."""
    server = FakeServer()

    result = download.download_file(URL, FILENAME, transport=server, sleep=FakeSleep())

    assert result.size == len(BODY)
    assert result.sha256 == _sha(BODY)


def test_t15_rn01_overwrites_a_stale_file_with_the_same_name(home, download):
    """RN-03: a leftover file from an earlier build is not mistaken for the new one."""
    _destination().parent.mkdir(parents=True, exist_ok=True)
    _destination().write_bytes(b"stale bytes from an older fictional build" * 40)
    server = FakeServer(etag=None)

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert _destination().read_bytes() == BODY
    assert result.sha256 == _sha(BODY)


def test_t15_rn29_requests_send_a_descriptive_user_agent_and_an_accept_header(home, download):
    """RN-29, plan section 10: requests send a descriptive User-Agent and an Accept header."""
    server = FakeServer(cuts=[40])

    download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert len(server.requests) == 2
    for _, headers in server.requests:
        agent = headers.get("user-agent", "")
        assert agent.strip(), "every request names its client"
        assert not agent.lower().startswith("python-urllib"), "the default urllib agent is not descriptive"
        compact = agent.lower().replace(" ", "").replace("-", "").replace("_", "")
        assert "cardfactory" in compact, f"the User-Agent names the application: {agent!r}"
        assert headers.get("accept", "").strip(), "every request sends an Accept header"


# ---------------------------------------------------------------- resume


def test_t15_rn03_resumes_with_if_range_etag_after_a_dropped_connection(home, download):
    """RN-03, plan section 7: after a drop, the download resumes with Range and If-Range (ETag)."""
    server = FakeServer(cuts=[48])
    sleep = FakeSleep()

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep)

    assert len(server.requests) == 2
    retry = server.requests[1][1]
    assert retry.get("range", "").replace(" ", "") == "bytes=48-"
    assert retry.get("if-range") == ETAG
    assert _destination().read_bytes() == BODY
    assert result.size == len(BODY)
    assert result.sha256 == _sha(BODY)
    assert len(sleep.calls) == 1


def test_t15_rn03_resumes_with_if_range_last_modified_when_there_is_no_etag(home, download):
    """RN-03, plan section 7: with no ETag, If-Range carries the Last-Modified date."""
    server = FakeServer(etag=None, last_modified=LAST_MODIFIED, cuts=[32])

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    retry = server.requests[1][1]
    assert retry.get("range", "").replace(" ", "") == "bytes=32-"
    assert retry.get("if-range") == LAST_MODIFIED
    assert result.sha256 == _sha(BODY)
    assert _destination().read_bytes() == BODY


def test_t15_ca07_a_new_run_resumes_the_partial_download_of_an_interrupted_one(home, download):
    """CA-07, RN-03: a run that failed mid-download leaves a partial file the next run resumes."""
    failing = FakeServer(cuts=[64, 0, 0])
    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=failing, sleep=FakeSleep())

    server = FakeServer()
    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    first = server.requests[0][1]
    assert first.get("range", "").replace(" ", "") == "bytes=64-"
    assert first.get("if-range") == ETAG
    assert result.sha256 == _sha(BODY)
    assert _destination().read_bytes() == BODY


def test_t15_rn03_starts_over_when_the_server_refuses_the_range(home, download):
    """RN-03: when the server answers 200 instead of 206, the download starts over, never appends."""
    server = FakeServer(accepts_ranges=False, cuts=[40])

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert server.requests[1][1].get("if-range") == ETAG, "the resume was attempted"
    assert _destination().read_bytes() == BODY
    assert result.size == len(BODY)
    assert result.sha256 == _sha(BODY)


def test_t15_rn03_starts_over_when_the_source_changed_since_the_partial_download(home, download):
    """RN-03, plan section 7: a source changed since the partial download starts over."""
    failing = FakeServer(cuts=[56, 0, 0])
    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=failing, sleep=FakeSleep())

    changed = FakeServer(body=NEW_BODY, etag=NEW_ETAG)
    result = download.download_file(
        URL, FILENAME, expected_size=len(NEW_BODY), transport=changed, sleep=FakeSleep()
    )

    assert changed.requests[0][1].get("if-range") == ETAG, "the old validator was offered"
    assert _destination().read_bytes() == NEW_BODY
    assert result.size == len(NEW_BODY)
    assert result.sha256 == _sha(NEW_BODY)


def test_t15_rn03_does_not_ask_for_a_range_without_a_validator(home, download):
    """RN-03: with neither ETag nor Last-Modified, a dropped download starts over without Range."""
    server = FakeServer(etag=None, last_modified=None, cuts=[40])

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert _range_requests(server) == []
    assert _destination().read_bytes() == BODY
    assert result.sha256 == _sha(BODY)


@pytest.mark.parametrize(
    "server_options",
    [
        {"cuts": [48]},
        {"etag": None, "last_modified": LAST_MODIFIED, "cuts": [16, 48]},
        {"accepts_ranges": False, "cuts": [40, 80]},
        {"etag": None, "cuts": [24]},
    ],
    ids=["etag", "last-modified", "range-refused", "no-validator"],
)
def test_t15_rn03_every_range_request_carries_if_range(home, download, server_options):
    """RN-03, plan section 7: a range is asked for only together with If-Range."""
    server = FakeServer(**server_options)

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    _assert_every_range_has_if_range(server)
    assert result.sha256 == _sha(BODY)


# ---------------------------------------------------------------- size check


def test_t15_rn03_size_different_from_the_listing_fails(home, download):
    """RN-03: a file whose size differs from the listing is not accepted."""
    server = FakeServer()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, expected_size=len(BODY) + 10, transport=server, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"
    assert str(caught.value).strip()


def test_t15_rn03_body_longer_than_the_listing_fails(home, download):
    """RN-03: a body larger than the size stated by the listing is not accepted."""
    server = FakeServer()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, expected_size=len(BODY) - 1, transport=server, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"


def test_t15_rn03_body_shorter_than_content_length_fails(home, download):
    """RN-03: a stream that ends cleanly before its Content-Length is a size mismatch."""
    truncated = FakeResponse(
        200,
        {"Content-Length": str(len(BODY)), "Accept-Ranges": "bytes"},
        BODY[: len(BODY) // 2],
    )
    server = FakeServer(script={0: truncated, 1: truncated, 2: truncated}, etag=None)

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, transport=server, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"


def test_t15_rn03_a_size_mismatch_never_returns_a_result(home, download):
    """RN-03: a short file with a matching Content-Length still fails against the listing."""
    short = BODY[:100]
    server = FakeServer(body=short)

    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())


# ---------------------------------------------------------------- failures and retries


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError(ConnectionRefusedError(errno.ECONNREFUSED, "Connection refused")),
        urllib.error.URLError(OSError("getaddrinfo failed")),
        TimeoutError("timed out"),
        ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"),
    ],
    ids=["refused", "no-name-resolution", "timeout", "reset"],
)
def test_t15_rn28_network_failure_is_tried_three_times_then_fails_with_its_cause(home, download, failure):
    """RN-28: no network is tried DOWNLOAD_ATTEMPTS times with a growing short pause, then fails."""
    server = FakeServer(script={0: failure, 1: failure, 2: failure, 3: failure})
    sleep = FakeSleep()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep)

    assert len(server.requests) == download.DOWNLOAD_ATTEMPTS == 3
    assert caught.value.code == "source_unreachable"
    assert str(caught.value).strip()
    assert len(sleep.calls) == 2, "a pause between attempts, none after the last"
    assert all(0 < seconds <= 60 for seconds in sleep.calls), "the pause is short"
    assert sleep.calls[0] < sleep.calls[1], "the pause grows"


@pytest.mark.parametrize("status", [500, 503, 404, 403])
def test_t15_rn28_source_failure_is_tried_three_times_then_fails_with_its_cause(home, download, status):
    """RN-28: an error status from the data source is retried, then reported as a source failure."""
    failed = FakeResponse(status, {"Content-Length": "0"})
    server = FakeServer(script={0: failed, 1: failed, 2: failed, 3: failed})
    sleep = FakeSleep()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep)

    assert len(server.requests) == 3
    assert caught.value.code == "source_unreachable"
    assert len(sleep.calls) == 2


def test_t15_rn28_no_network_and_source_failure_state_different_causes(home, download):
    """RN-28: the person sees the cause: no network reads differently from a source failure."""
    offline_error = urllib.error.URLError(OSError("getaddrinfo failed"))
    offline = FakeServer(script={n: offline_error for n in range(3)})
    failing_response = FakeResponse(503, {"Content-Length": "0"})
    failing = FakeServer(script={n: failing_response for n in range(3)})

    with pytest.raises(download.DownloadError) as no_network:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=offline, sleep=FakeSleep())
    with pytest.raises(download.DownloadError) as source_failure:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=failing, sleep=FakeSleep())

    assert str(no_network.value).strip()
    assert str(source_failure.value).strip()
    assert str(no_network.value) != str(source_failure.value)


def test_t15_rn28_success_on_a_later_attempt(home, download):
    """RN-28: a download that fails twice and then succeeds returns the full file."""
    offline_error = urllib.error.URLError(OSError("getaddrinfo failed"))
    server = FakeServer(script={0: offline_error, 1: FakeResponse(502, {"Content-Length": "0"})})
    sleep = FakeSleep()

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep)

    assert len(server.requests) == 3
    assert len(sleep.calls) == 2
    assert result.sha256 == _sha(BODY)
    assert _destination().read_bytes() == BODY


def test_t15_rn28_dropped_connections_on_every_attempt_fail_after_three(home, download):
    """RN-28: a connection that drops mid-stream on every attempt fails after three attempts."""
    server = FakeServer(cuts=[16, 16, 16, 16])

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert len(server.requests) == 3
    assert caught.value.code == "source_unreachable"


def test_t15_rn28_disk_full_fails_with_insufficient_space(home, download):
    """RN-28, RN-03: a full disk during the download fails with its cause (insufficient_space)."""
    server = FakeServer(script={})
    sleep = FakeSleep()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(
            URL,
            FILENAME,
            expected_size=len(BODY),
            transport=server,
            sleep=sleep,
            open_file=disk_full_open,
        )

    assert caught.value.code == "insufficient_space"
    assert str(caught.value).strip()
    assert len(server.requests) == 1, "a full disk is not retried"
    assert sleep.calls == []


def test_t15_rn28_disk_full_cause_differs_from_no_network(home, download):
    """RN-28: the disk-full cause is stated apart from a network failure."""
    offline_error = urllib.error.URLError(OSError("getaddrinfo failed"))
    offline = FakeServer(script={n: offline_error for n in range(3)})

    with pytest.raises(download.DownloadError) as disk_full:
        download.download_file(
            URL, FILENAME, expected_size=len(BODY), transport=FakeServer(), sleep=FakeSleep(), open_file=disk_full_open
        )
    with pytest.raises(download.DownloadError) as no_network:
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=offline, sleep=FakeSleep())

    assert str(disk_full.value) != str(no_network.value)


# ---------------------------------------------------------------- download listing
#
# catalog.download.read_listing(*, transport, sleep) -> dict[str, ListingEntry]
#     GETs the Scryfall bulk-data listing (LISTING_URL below) with the same
#     User-Agent, Accept header and DOWNLOAD_ATTEMPTS retry as a download, and
#     returns one entry per registry source, keyed by its name
#     ("scryfall_oracle"). ListingEntry has `.url` (download_uri), `.size` (int)
#     and `.published_at` (aware datetime from updated_at). A network failure,
#     a non-2xx status, malformed JSON or a missing entry raises DownloadError
#     with code `source_unreachable`. Every value below is fictional.

LISTING_URL = "https://api.scryfall.com/bulk-data"
ORACLE_URI = "https://data.scryfall.io/oracle-cards/oracle-cards-20261108090000.json"


def _listing_entry(**overrides):
    entry = {
        "object": "bulk_data",
        "id": "00000000-0000-4000-8000-000000000001",
        "type": "oracle_cards",
        "name": "Fictional Oracle Cards",
        "download_uri": ORACLE_URI,
        "updated_at": "2026-11-08T22:04:23.142+00:00",
        "size": 171234567,
        "content_type": "application/json",
        "content_encoding": "gzip",
    }
    entry.update(overrides)
    return entry


def _without(key):
    return {name: value for name, value in _listing_entry().items() if name != key}


def _listing_body(*entries):
    if not entries:
        entries = (
            _listing_entry(
                id="00000000-0000-4000-8000-000000000002",
                type="default_cards",
                download_uri="https://data.scryfall.io/default-cards/default-cards-20261108090000.json",
                size=999,
            ),
            _listing_entry(),
        )
    return json.dumps({"object": "list", "has_more": False, "data": list(entries)}).encode("utf-8")


class ListingTransport:
    """Answers each request with the next scripted step; the last step repeats.

    A step is an exception to raise, or a tuple `(body,)` / `(body, status)`.
    """

    def __init__(self, *steps):
        self.steps = list(steps)
        self.requests = []

    def __call__(self, url, headers):
        self.requests.append((url, {str(name).lower(): value for name, value in dict(headers).items()}))
        step = self.steps[min(len(self.requests) - 1, len(self.steps) - 1)]
        if isinstance(step, BaseException):
            raise step
        body = step[0]
        status = step[1] if len(step) > 1 else 200
        return FakeResponse(
            status,
            {"Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(body))},
            body,
        )


def test_t15_rn28_listing_returns_the_oracle_entry_keyed_by_source_name(home, download):
    """RN-28, RN-01: the listing states the address, size and publication date of a source."""
    transport = ListingTransport((_listing_body(),))

    listing = download.read_listing(transport=transport, sleep=FakeSleep())

    entry = listing["scryfall_oracle"]
    assert entry.url == ORACLE_URI
    assert entry.size == 171234567
    assert isinstance(entry.size, int)
    assert entry.published_at == datetime.datetime(2026, 11, 8, 22, 4, 23, 142000, tzinfo=datetime.timezone.utc)
    assert entry.published_at.tzinfo is not None
    assert transport.requests[0][0] == LISTING_URL


def test_t15_rn28_listing_has_an_entry_for_every_registry_source(home, download):
    """RN-28, plan section 7: the setup size is the sum over the registry, so each source is listed."""
    from catalog.sources import SOURCES

    listing = download.read_listing(transport=ListingTransport((_listing_body(),)), sleep=FakeSleep())

    assert {source.name for source in SOURCES} <= set(listing)


def test_t15_rn29_listing_request_sends_user_agent_and_accept(home, download):
    """RN-29, plan section 10: the listing request sends a descriptive User-Agent and Accept."""
    transport = ListingTransport((_listing_body(),))

    download.read_listing(transport=transport, sleep=FakeSleep())

    headers = transport.requests[0][1]
    agent = headers.get("user-agent", "")
    assert not agent.lower().startswith("python-urllib")
    assert "cardfactory" in agent.lower().replace(" ", "").replace("-", "").replace("_", "")
    assert headers.get("accept", "").strip()


def test_t15_rn28_listing_network_failure_is_tried_three_times(home, download):
    """RN-28: an unreachable listing is tried DOWNLOAD_ATTEMPTS times with growing pauses, then fails."""
    transport = ListingTransport(urllib.error.URLError(OSError("getaddrinfo failed")))
    sleep = FakeSleep()

    with pytest.raises(download.DownloadError) as caught:
        download.read_listing(transport=transport, sleep=sleep)

    assert len(transport.requests) == download.DOWNLOAD_ATTEMPTS
    assert caught.value.code == "source_unreachable"
    assert str(caught.value).strip()
    assert len(sleep.calls) == 2
    assert sleep.calls[0] < sleep.calls[1]


def test_t15_rn28_listing_succeeds_on_a_later_attempt(home, download):
    """RN-28: a listing that fails once and then answers is read."""
    transport = ListingTransport(TimeoutError("timed out"), (_listing_body(),))

    listing = download.read_listing(transport=transport, sleep=FakeSleep())

    assert listing["scryfall_oracle"].url == ORACLE_URI
    assert len(transport.requests) == 2


@pytest.mark.parametrize("status", [500, 503, 404, 429])
def test_t15_rn28_listing_error_status_fails_with_source_unreachable(home, download, status):
    """RN-28: a non-2xx listing answer is retried, then reported as a source failure."""
    transport = ListingTransport((b'{"object": "error"}', status))

    with pytest.raises(download.DownloadError) as caught:
        download.read_listing(transport=transport, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"
    assert len(transport.requests) == download.DOWNLOAD_ATTEMPTS


MALFORMED_LISTINGS = {
    "empty": b"",
    "html": b"<html>maintenance</html>",
    "truncated-json": b'{"object": "list", "data": [',
    "not-utf8": b"\xff\xfe\x00not utf-8",
    "null": b"null",
    "array": b"[]",
    "no-data": b'{"object": "list"}',
    "data-not-list": b'{"object": "list", "data": {}}',
    "entry-not-object": b'{"object": "list", "data": ["oracle_cards"]}',
    "no-oracle-entry": _listing_body(_listing_entry(type="default_cards")),
    "uri-null": _listing_body(_listing_entry(download_uri=None)),
    "uri-empty": _listing_body(_listing_entry(download_uri="")),
    "uri-missing": _listing_body(_without("download_uri")),
    "size-missing": _listing_body(_without("size")),
    "date-missing": _listing_body(_without("updated_at")),
    "size-text": _listing_body(_listing_entry(size="large")),
    "size-negative": _listing_body(_listing_entry(size=-5)),
    "size-null": _listing_body(_listing_entry(size=None)),
    "size-fraction": _listing_body(_listing_entry(size=12.5)),
    "size-bool": _listing_body(_listing_entry(size=True)),
    "date-text": _listing_body(_listing_entry(updated_at="yesterday")),
    "date-null": _listing_body(_listing_entry(updated_at=None)),
    "date-number": _listing_body(_listing_entry(updated_at=20261108)),
}


@pytest.mark.parametrize("body", list(MALFORMED_LISTINGS.values()), ids=list(MALFORMED_LISTINGS))
def test_t15_rn28_malformed_listing_fails_with_source_unreachable(home, download, body):
    """RN-28: a malformed listing is reported as a source failure, never a crash."""
    transport = ListingTransport((body,))

    with pytest.raises(download.DownloadError) as caught:
        download.read_listing(transport=transport, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"
    assert str(caught.value).strip()


def test_t15_rn28_listing_keeps_a_size_beyond_32_bits_exact(home, download):
    """RN-28: a size beyond 32 bits (bulk files reach gigabytes) is kept exactly."""
    huge = 9_876_543_210_123
    transport = ListingTransport((_listing_body(_listing_entry(size=huge)),))

    listing = download.read_listing(transport=transport, sleep=FakeSleep())

    assert listing["scryfall_oracle"].size == huge


def test_t15_rn28_listing_ignores_unknown_entries_and_fields(home, download):
    """RN-28: extra bulk files, extra fields and odd characters in the listing do not break it."""
    body = _listing_body(
        _listing_entry(type="rulings", download_uri="https://data.scryfall.io/rulings/rulings-20261108090000.json", extra={"a": 1}),
        _listing_entry(name="Fictional Oracle Cards éçã — \U0001F0A1", unknown_field=[1, 2]),
    )

    listing = download.read_listing(transport=ListingTransport((body,)), sleep=FakeSleep())

    assert listing["scryfall_oracle"].url == ORACLE_URI


@pytest.mark.parametrize(
    "uri",
    [
        "http://data.scryfall.io/oracle-cards/oracle-cards-20261108090000.json",
        "https://evil.example/x",
        "https://data.scryfall.io.evil.example/x",
        "https://api.scryfall.com@evil.example/x",
        "https://user:pass@data.scryfall.io/oracle-cards/x.json",
        "ftp://data.scryfall.io/oracle-cards/x.json",
        "file:///C:/Windows/win.ini",
        "//evil.example/x",
        "/oracle-cards/x.json",
        "https://",
    ],
    ids=[
        "plain-http",
        "other-host",
        "lookalike-host",
        "userinfo-to-other-host",
        "userinfo-on-scryfall",
        "ftp",
        "file",
        "scheme-relative",
        "relative",
        "no-host",
    ],
)
def test_t15_rn29_listing_refuses_a_download_address_outside_scryfall(home, download, uri):
    """RN-29, CLAUDE.md: the application contacts only the data sources, over HTTPS."""
    transport = ListingTransport((_listing_body(_listing_entry(download_uri=uri)),))

    with pytest.raises(download.DownloadError) as caught:
        download.read_listing(transport=transport, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"


# ---------------------------------------------------------------- redirects


def _redirect_handler_classes(module):
    return [
        value
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, urllib.request.HTTPRedirectHandler)
        and value is not urllib.request.HTTPRedirectHandler
    ]


def _redirect(handler, new_url, code=302):
    request = urllib.request.Request(LISTING_URL, headers={"User-Agent": "CardFactory/test"})
    try:
        return handler.redirect_request(
            request, io.BytesIO(b""), code, "Found", _headers({"Location": new_url}), new_url
        )
    except (urllib.error.URLError, OSError):
        return None


def test_t15_rn29_download_module_exposes_one_redirect_handler(download):
    """RN-29: the urllib transport follows redirects only through a handler of its own."""
    assert len(_redirect_handler_classes(download)) == 1


@pytest.mark.parametrize(
    "new_url",
    [
        "http://data.scryfall.io/oracle-cards/x.json",
        "https://evil.example/x",
        "https://data.scryfall.io.evil.example/x",
        "https://api.scryfall.com@evil.example/x",
        "ftp://data.scryfall.io/x.json",
        "file:///C:/Windows/win.ini",
    ],
    ids=["plain-http", "other-host", "lookalike-host", "userinfo", "ftp", "file"],
)
def test_t15_rn29_redirect_handler_refuses_redirects_outside_scryfall(download, new_url):
    """RN-29, CLAUDE.md: a redirect never leads the application to another host or to plain HTTP."""
    (handler_class,) = _redirect_handler_classes(download)

    assert _redirect(handler_class(), new_url) is None


@pytest.mark.parametrize(
    "new_url",
    [
        "https://data.scryfall.io/oracle-cards/oracle-cards-20261108090000.json",
        "https://api.scryfall.com/bulk-data",
    ],
)
def test_t15_rn29_redirect_handler_allows_scryfall_over_https(download, new_url):
    """RN-29: a redirect within the data source's hosts over HTTPS is followed."""
    (handler_class,) = _redirect_handler_classes(download)

    followed = _redirect(handler_class(), new_url)

    assert followed is not None
    assert followed.full_url == new_url


# ---------------------------------------------------------------- stricter size and range checks


class OpenRecorder:
    """The real `open`, recording each (file name, mode)."""

    def __init__(self):
        self.calls = []

    def __call__(self, path, mode="r", *args, **kwargs):
        self.calls.append((Path(path).name, mode))
        return open(path, mode, *args, **kwargs)

    def data_writes(self):
        names = {FILENAME, FILENAME + ".part"}
        return [(name, mode) for name, mode in self.calls if name in names and any(f in mode for f in "wax+")]


def _leave_partial(download, size=64, **server_options):
    """Run a download that drops after `size` bytes on every attempt, leaving a partial file."""
    failing = FakeServer(cuts=[size] * download.DOWNLOAD_ATTEMPTS, **server_options)
    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=failing, sleep=FakeSleep())


def test_t15_rn03_content_length_different_from_listing_is_never_written(home, download):
    """RN-03: a 200 whose Content-Length differs from the listing size is refused before writing."""
    server = FakeServer()
    recorder = OpenRecorder()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(
            URL, FILENAME, expected_size=len(BODY) + 7, transport=server, sleep=FakeSleep(), open_file=recorder
        )

    assert caught.value.code == "source_unreachable"
    assert recorder.data_writes() == []


def test_t15_rn03_content_range_total_different_from_listing_is_never_written(home, download):
    """RN-03: a 206 whose Content-Range total differs from the listing size is refused before writing."""
    _leave_partial(download)
    grown = FakeServer(body=BODY + b"[extra fictional bytes]")
    recorder = OpenRecorder()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(
            URL, FILENAME, expected_size=len(BODY), transport=grown, sleep=FakeSleep(), open_file=recorder
        )

    assert grown.requests[0][1].get("if-range") == ETAG, "the resume was attempted"
    assert caught.value.code == "source_unreachable"
    assert recorder.data_writes() == []


def test_t15_rn03_a_416_discards_the_partial_and_starts_over_without_range(home, download):
    """RN-03: a range the server cannot satisfy (416) drops the partial file; the next request has no Range."""
    _leave_partial(download)
    unsatisfiable = FakeResponse(416, {"Content-Range": f"bytes */{len(BODY)}", "Content-Length": "0"})
    server = FakeServer(script={0: unsatisfiable})

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert "range" in server.requests[0][1]
    assert "range" not in server.requests[1][1]
    assert _destination().read_bytes() == BODY
    assert result.sha256 == _sha(BODY)


def test_t15_rn03_a_416_that_ends_a_run_leaves_no_partial_to_resume(home, download):
    """RN-03: after a run that only got 416 answers, the next run starts over without Range."""
    _leave_partial(download)
    unsatisfiable = FakeResponse(416, {"Content-Range": f"bytes */{len(BODY)}", "Content-Length": "0"})
    refusing = FakeServer(script={n: unsatisfiable for n in range(download.DOWNLOAD_ATTEMPTS)})
    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, expected_size=len(BODY), transport=refusing, sleep=FakeSleep())

    server = FakeServer()
    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert "range" not in server.requests[0][1]
    assert result.sha256 == _sha(BODY)


def test_t15_rn03_a_206_starting_elsewhere_than_the_partial_is_discarded(home, download):
    """RN-03: a 206 whose Content-Range does not start at the partial size is not appended."""
    _leave_partial(download, size=64)
    wrong_start = FakeResponse(
        206,
        {"ETag": ETAG, "Content-Range": f"bytes 32-{len(BODY) - 1}/{len(BODY)}", "Content-Length": str(len(BODY) - 32)},
        BODY[32:],
    )
    server = FakeServer(script={0: wrong_start})

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert "range" not in server.requests[1][1], "the partial file was dropped"
    assert _destination().read_bytes() == BODY
    assert result.sha256 == _sha(BODY)


def test_t15_rn03_a_206_with_unknown_total_and_no_listing_size_fails(home, download):
    """RN-03: with no listing size, a 206 whose Content-Range total is '*' cannot be checked and fails."""
    failing = FakeServer(cuts=[64] * download.DOWNLOAD_ATTEMPTS)
    with pytest.raises(download.DownloadError):
        download.download_file(URL, FILENAME, transport=failing, sleep=FakeSleep())
    unknown_total = FakeResponse(
        206,
        {"ETag": ETAG, "Content-Range": f"bytes 64-{len(BODY) - 1}/*", "Content-Length": str(len(BODY) - 64)},
        BODY[64:],
    )
    server = FakeServer(script={n: unknown_total for n in range(download.DOWNLOAD_ATTEMPTS)})

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(URL, FILENAME, transport=server, sleep=FakeSleep())

    assert caught.value.code == "source_unreachable"
    assert not _destination().exists()


# ---------------------------------------------------------------- weak validators and Windows disk full


def test_t15_rn03_a_weak_etag_is_not_used_in_if_range(home, download):
    """RN-03: If-Range needs a strong validator, so a weak ETag yields to Last-Modified."""
    server = FakeServer(etag='W/"fictional-weak"', last_modified=LAST_MODIFIED, cuts=[40])

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    for _, headers in server.requests:
        assert not str(headers.get("if-range", "")).startswith("W/")
    assert server.requests[1][1].get("if-range") == LAST_MODIFIED
    assert result.sha256 == _sha(BODY)


def test_t15_rn03_a_weak_etag_alone_does_not_resume(home, download):
    """RN-03: with only a weak ETag there is no usable validator, so no Range is asked for."""
    server = FakeServer(etag='W/"fictional-weak"', last_modified=None, cuts=[40])

    result = download.download_file(URL, FILENAME, expected_size=len(BODY), transport=server, sleep=FakeSleep())

    assert _range_requests(server) == []
    assert result.sha256 == _sha(BODY)


class WindowsDiskFull(OSError):
    """A full disk as Windows reports it: ERROR_DISK_FULL (112), with no ENOSPC errno."""

    winerror = 112

    def __init__(self):
        super().__init__(errno.EIO, "There is not enough space on the disk")


class WindowsDiskFullFile(DiskFullFile):
    def write(self, data):
        raise WindowsDiskFull()


def windows_disk_full_open(path, mode="rb", *args, **kwargs):
    handle = open(path, mode, *args, **kwargs)
    if any(flag in mode for flag in "wax+"):
        return WindowsDiskFullFile(handle)
    return handle


def test_t15_rn28_windows_disk_full_fails_with_insufficient_space(home, download):
    """RN-28, RN-03: a full disk reported by winerror 112 fails at once with insufficient_space."""
    server = FakeServer()
    sleep = FakeSleep()

    with pytest.raises(download.DownloadError) as caught:
        download.download_file(
            URL, FILENAME, expected_size=len(BODY), transport=server, sleep=sleep, open_file=windows_disk_full_open
        )

    assert caught.value.code == "insufficient_space"
    assert len(server.requests) == 1
    assert sleep.calls == []
