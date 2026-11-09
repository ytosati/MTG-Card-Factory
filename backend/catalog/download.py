"""Source downloader: the data source listing and resumable downloads to `data/downloads/`.
Details: specs/plan.md, sections 7 ("All-or-nothing build", phase 1) and 10.
"""

import errno
import hashlib
import http.client
import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from catalog import sources
from core.errors import CODE_INTERNAL
from core.instance import instance_snapshot
from core.paths import data_dir

logger = logging.getLogger(__name__)

# Attempts in all for one download (see spec RN-28).
DOWNLOAD_ATTEMPTS = 3
PAUSE_STEP_SECONDS = 2
LISTING_URL = "https://api.scryfall.com/bulk-data"
ACCEPT = "application/json;q=0.9,*/*;q=0.8"
READ_SIZE = 64 * 1024
TIMEOUT_SECONDS = 60
PARTIAL_SUFFIX = ".part"
VALIDATOR_SUFFIX = ".part.json"

CODE_SOURCE_UNREACHABLE = "source_unreachable"
CODE_INSUFFICIENT_SPACE = "insufficient_space"

NO_NETWORK_MESSAGE = (
    "Could not reach the data source: there is no network connection or the connection dropped. "
    "Check the internet connection and try again."
)
SECURE_CONNECTION_MESSAGE = (
    "Could not open a secure connection to the data source. Check the computer's date and time, "
    "and any antivirus or proxy that inspects connections, then try again."
)
SOURCE_FAILURE_MESSAGE = "The data source answered with an error (HTTP {status}). Try again later."
SIZE_MISMATCH_MESSAGE = "The downloaded file does not have the size stated by the data source. Try again later."
LISTING_MESSAGE = "The data source sent a file list that could not be read. Try again later."
DISK_FULL_MESSAGE = "The disk that holds the data folder is full. Free some space and try again."
FILE_FAILURE_MESSAGE = (
    "Could not write the downloaded file in the data folder. Check that Card Factory can write "
    "to it and that no other program holds the file, then try again."
)

# Windows reports a full disk as ERROR_HANDLE_DISK_FULL (39) or ERROR_DISK_FULL (112).
_DISK_FULL_WINERRORS = (39, 112)


class DownloadError(Exception):
    """A download that failed for good; `code` is an error code of plan section 6."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class _AttemptFailed(Exception):
    """One failed attempt, retried while attempts remain."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class DownloadResult:
    """A complete downloaded file, with the values recorded in its source record."""

    path: Path
    size: int
    sha256: str


@dataclass(frozen=True)
class ListingEntry:
    """One file of the data source listing."""

    url: str
    size: int
    published_at: datetime


def request_headers():
    """The headers every request to a data source sends (see spec RN-29)."""
    version = instance_snapshot().version
    return {
        "User-Agent": f"CardFactory/{version} (local Commander card generator)",
        "Accept": ACCEPT,
    }


def allowed_hosts():
    """Every host a data source may be read from: the union over the registry."""
    return frozenset(host for source in sources.SOURCES for host in source.allowed_hosts)


def is_allowed_url(url, hosts):
    """True for an https URL on one of `hosts`, with no credentials and the default port."""
    try:
        parts = urlsplit(url)
        port = parts.port
    except (TypeError, ValueError, AttributeError):
        return False
    return (
        parts.scheme == "https"
        and parts.hostname in hosts
        and parts.username is None
        and parts.password is None
        and port in (None, 443)
    )


def read_listing(*, transport=None, sleep=None):
    """The listing entry of each registry source, keyed by source name."""
    transport, sleep = _seams(transport, sleep)
    return _with_attempts(lambda: _read_listing_once(transport), sleep)


def download_file(url, filename, *, expected_size=None, transport=None, sleep=None, open_file=open):
    """Download `url` to `data/downloads/<filename>`, resuming a partial download when possible."""
    transport, sleep = _seams(transport, sleep)
    # Network errors become attempt failures inside; an OSError that reaches here
    # comes from the data folder (writer, hash, rename).
    try:
        folder = data_dir() / "downloads"
        folder.mkdir(parents=True, exist_ok=True)
        target = _Target(folder / filename, url, open_file)
        size = _with_attempts(lambda: _download_once(target, transport, expected_size), sleep)
        sha256 = target.digest()
        os.replace(target.partial, target.path)
        target.forget_validator()
    except OSError as error:
        raise _file_failure(error) from None
    return DownloadResult(path=target.path, size=size, sha256=sha256)


class AllowedHostsRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to https on an allowed host (see spec RN-29)."""

    def __init__(self, hosts=None):
        super().__init__()
        self.hosts = frozenset(hosts) if hosts is not None else allowed_hosts()

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not is_allowed_url(newurl, self.hosts):
            raise urllib.error.URLError("redirect to a host that is not a data source refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urllib_transport(url, headers):
    """The production transport over urllib; tests pass a fake one instead."""
    hosts = allowed_hosts()
    if not is_allowed_url(url, hosts):
        raise urllib.error.URLError("address that is not a data source refused")
    opener = urllib.request.build_opener(AllowedHostsRedirectHandler(hosts))
    request = urllib.request.Request(url, headers=headers)
    try:
        response = opener.open(request, timeout=TIMEOUT_SECONDS)
    except urllib.error.HTTPError as error:
        # An error status is an answer from the source, not a network failure.
        return _UrllibResponse(error.code, error.headers, error)
    except http.client.HTTPException as error:
        raise ConnectionError(str(error)) from error
    return _UrllibResponse(response.status, response.headers, response)


class _UrllibResponse:
    def __init__(self, status, headers, stream):
        self.status = status
        self.headers = headers
        self._stream = stream

    @property
    def chunks(self):
        return self._read()

    def _read(self):
        while True:
            try:
                chunk = self._stream.read(READ_SIZE)
            except http.client.HTTPException as error:
                # IncompleteRead and friends are dropped connections too.
                raise ConnectionError(str(error)) from error
            if not chunk:
                return
            yield chunk

    def close(self):
        self._stream.close()


def _seams(transport, sleep):
    if transport is None:
        transport = urllib_transport
    if sleep is None:
        sleep = time.sleep
    return transport, sleep


def _with_attempts(attempt, sleep):
    for number in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            return attempt()
        except _AttemptFailed as failure:
            logger.warning("Download attempt %s of %s failed: %s", number, DOWNLOAD_ATTEMPTS, failure.message)
            if number == DOWNLOAD_ATTEMPTS:
                raise DownloadError(CODE_SOURCE_UNREACHABLE, failure.message) from None
            sleep(PAUSE_STEP_SECONDS * number)
    raise AssertionError("unreachable")


def _network_failure(error):
    if isinstance(error, ssl.SSLError) or isinstance(getattr(error, "reason", None), ssl.SSLError):
        return _AttemptFailed(SECURE_CONNECTION_MESSAGE)
    return _AttemptFailed(NO_NETWORK_MESSAGE)


def _file_failure(error):
    if error.errno == errno.ENOSPC or getattr(error, "winerror", None) in _DISK_FULL_WINERRORS:
        # A full disk fails at once, with no retry (see spec RN-28).
        return DownloadError(CODE_INSUFFICIENT_SPACE, DISK_FULL_MESSAGE)
    return DownloadError(CODE_INTERNAL, FILE_FAILURE_MESSAGE)


def _open(transport, url, headers):
    try:
        return transport(url, headers)
    except OSError as error:
        raise _network_failure(error) from None


def _read_listing_once(transport):
    response = _open(transport, LISTING_URL, request_headers())
    try:
        if not 200 <= response.status < 300:
            raise _AttemptFailed(SOURCE_FAILURE_MESSAGE.format(status=response.status))
        try:
            body = b"".join(response.chunks)
        except OSError as error:
            raise _network_failure(error) from None
    finally:
        response.close()
    try:
        files = json.loads(body)["data"]
        by_type = {item["type"]: item for item in files if isinstance(item, dict) and "type" in item}
        return {
            source.name: _listing_entry(by_type[source.listing_type], source.allowed_hosts)
            for source in sources.SOURCES
        }
    except (ValueError, TypeError, KeyError):
        raise _AttemptFailed(LISTING_MESSAGE) from None


def _listing_entry(item, hosts):
    url, size = item["download_uri"], item["size"]
    published_at = datetime.fromisoformat(item["updated_at"])
    if not isinstance(url, str) or not is_allowed_url(url, hosts):
        raise ValueError("download_uri")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError("size")
    if published_at.tzinfo is None:
        raise ValueError("updated_at")
    return ListingEntry(url=url, size=size, published_at=published_at)


class _Target:
    """The partial file of one download and the validator that lets it resume."""

    def __init__(self, path, url, open_file):
        self.path = path
        self.url = url
        self.partial = path.with_name(path.name + PARTIAL_SUFFIX)
        self.validator_file = path.with_name(path.name + VALIDATOR_SUFFIX)
        self.open_file = open_file

    def resume_point(self, expected_size):
        """(offset, If-Range value) of a partial download that may resume, else (0, None)."""
        try:
            saved = json.loads(self.validator_file.read_text(encoding="utf-8"))
            offset = self.partial.stat().st_size
        except (OSError, ValueError):
            return 0, None
        if not isinstance(saved, dict) or saved.get("url") != self.url or not saved.get("if_range"):
            return 0, None
        if offset == 0 or (expected_size is not None and offset >= expected_size):
            return 0, None
        return offset, str(saved["if_range"])

    def keep_validator(self, headers):
        # If-Range needs a strong ETag; Last-Modified is the fallback (see specs/plan.md, section 7).
        etag = headers.get("ETag")
        if etag and etag.strip().startswith("W/"):
            etag = None
        value = etag or headers.get("Last-Modified")
        if not value:
            self.forget_validator()
            return
        data = json.dumps({"url": self.url, "if_range": value}).encode("utf-8")
        with self.open_file(self.validator_file, "wb") as handle:
            handle.write(data)

    def forget_validator(self):
        self.validator_file.unlink(missing_ok=True)

    def digest(self):
        sha = hashlib.sha256()
        with self.open_file(self.partial, "rb") as handle:
            while chunk := handle.read(READ_SIZE):
                sha.update(chunk)
        return sha.hexdigest()

    def discard(self):
        self.partial.unlink(missing_ok=True)
        self.forget_validator()


def _download_once(target, transport, expected_size):
    offset, if_range = target.resume_point(expected_size)
    headers = request_headers()
    if if_range:
        headers["Range"] = f"bytes={offset}-"
        headers["If-Range"] = if_range
    response = _open(transport, target.url, headers)
    try:
        return _receive(target, response, offset, expected_size)
    finally:
        response.close()


def _receive(target, response, offset, expected_size):
    if response.status == 206 and offset:
        total = _content_range_total(response.headers)
        if _content_range_start(response.headers) != offset or total is None:
            target.discard()
            raise _AttemptFailed(SOURCE_FAILURE_MESSAGE.format(status=response.status))
        if expected_size is not None and total != expected_size:
            target.discard()
            raise _AttemptFailed(SIZE_MISMATCH_MESSAGE)
        expected, mode, written = total, "ab", offset
    elif response.status == 200:
        announced = _content_length(response.headers)
        if expected_size is not None and announced is not None and announced != expected_size:
            raise _AttemptFailed(SIZE_MISMATCH_MESSAGE)
        # Range refused or source changed: the partial file is dropped (see spec RN-03).
        target.keep_validator(response.headers)
        expected = expected_size if expected_size is not None else announced
        mode, written = "wb", 0
    else:
        if response.status == 416:
            target.discard()
        raise _AttemptFailed(SOURCE_FAILURE_MESSAGE.format(status=response.status))

    chunks = iter(response.chunks)
    with target.open_file(target.partial, mode) as handle:
        while expected is None or written <= expected:
            try:
                chunk = next(chunks)
            except StopIteration:
                break
            except OSError as error:
                raise _network_failure(error) from None
            handle.write(chunk)
            written += len(chunk)
    if expected is not None and written != expected:
        target.discard()
        raise _AttemptFailed(SIZE_MISMATCH_MESSAGE)
    return written


def _content_length(headers):
    try:
        return int(headers.get("Content-Length"))
    except (TypeError, ValueError):
        return None


def _content_range_start(headers):
    try:
        return int(headers.get("Content-Range", "").split(" ", 1)[1].split("-", 1)[0])
    except (IndexError, ValueError):
        return None


def _content_range_total(headers):
    try:
        return int(headers.get("Content-Range", "").rsplit("/", 1)[1])
    except (IndexError, ValueError):
        return None
