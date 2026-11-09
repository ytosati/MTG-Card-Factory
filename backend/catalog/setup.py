"""Setup service: download size, free space, the build job to show and starting the build.
Details: specs/plan.md, sections 6 (setup, readiness gate) and 7 (catalog version, build).
"""

import logging
import shutil
import threading
from dataclasses import dataclass

from django.db import DatabaseError

from catalog import build, download, sources
from catalog.selectors import is_ready
from core import jobs
from core.config import get_config
from core.errors import MappedError, error_body
from core.models import Job
from core.paths import data_dir
from core.selectors import ACTIVE_STATUSES, active_build_job_ids, latest_build_job_id
from core.status import settings_list

logger = logging.getLogger(__name__)

# Free space needed per downloaded byte: the downloads, the database and the
# write-ahead log of the import (see spec RN-28, CA-60).
BUILD_SPACE_FACTOR = 3
# The screen polls: one quick attempt per poll, the next poll is the retry.
POLL_LISTING_ATTEMPTS = 1

CODE_INSUFFICIENT_SPACE = download.CODE_INSUFFICIENT_SPACE
INSUFFICIENT_SPACE_MESSAGE = (
    "There is not enough free space on the disk that holds the data folder to build the reference "
    "database. Free some space and try again."
)

_listing = None
_listing_lock = threading.Lock()
# Held while a poll reads the listing, so concurrent polls with an empty cache share one read.
_listing_read_lock = threading.Lock()
# Reentrant: a request made from inside a build that runs in the request's own thread may take it again.
_start_lock = threading.RLock()


@dataclass(frozen=True)
class SetupSnapshot:
    """What the Setup screen shows; sizes are in bytes, None when unknown."""

    database_ready: bool
    job: Job | None
    download_size: int | None
    space_needed: int | None
    free_space: int | None
    listing_error: dict | None
    settings: tuple


def clear_listing_cache():
    """Forget the cached data source listing, so the next read asks the source again."""
    global _listing
    with _listing_lock:
        _listing = None


def setup_snapshot():
    """The setup state; reads only the data source listing, never a data file (see spec CA-18)."""
    ready, job = _database_state()
    download_size = space_needed = listing_error = None
    # A ready database contacts no data source (see spec RN-01).
    if not ready:
        try:
            download_size = _download_size(_polled_listing())
            space_needed = download_size * BUILD_SPACE_FACTOR
        except download.DownloadError as error:
            listing_error = error_body(error.code, error.message, error.setting)
    return SetupSnapshot(
        database_ready=ready,
        job=job,
        download_size=download_size,
        space_needed=space_needed,
        free_space=free_space(),
        listing_error=listing_error,
        settings=settings_list(get_config()),
    )


def request_build():
    """The running build job, or a new one; raises MappedError when the listing or the free space fails.

    Call it outside `transaction.atomic()` (see core.jobs.submit).
    """
    running = _running_build()
    if running is not None:
        return running
    # A ready database needs no download: the build job ends done at once (see spec RN-03).
    if not is_ready():
        space_needed = _download_size(_listing_for_build()) * BUILD_SPACE_FACTOR
        free = free_space()
        # Unknown free space does not block: the build itself reports a full disk (see spec RN-28).
        if free is not None and free < space_needed:
            raise MappedError(CODE_INSUFFICIENT_SPACE, INSUFFICIENT_SPACE_MESSAGE)
    with _start_lock:
        running = _running_build()
        if running is not None:
            return running
        return build.start_build()


def free_space():
    """Free bytes on the drive that holds the data folder, or None when the disk cannot be read."""
    folder = data_dir()
    # Before the first start the data folder may not exist yet; its nearest existing parent is on the same drive.
    while not folder.exists() and folder.parent != folder:
        folder = folder.parent
    try:
        return shutil.disk_usage(folder).free
    except OSError:
        logger.exception("The free space of the data folder's disk could not be read.")
        return None


def _database_state():
    """(readiness, build job to show); a database that cannot be read is not ready and shows no job."""
    try:
        ready = is_ready()
        return ready, _job_to_show(ready)
    except DatabaseError:
        logger.exception("The setup could not read the database.")
        return False, None


def _cached_listing():
    with _listing_lock:
        return _listing


def _keep_listing(listing):
    global _listing
    with _listing_lock:
        _listing = listing


def _polled_listing():
    """The cached listing, or one quick read of it; a failure is not cached, so the next poll retries."""
    with _listing_read_lock:
        listing = _cached_listing()
        if listing is None:
            listing = download.read_listing(attempts=POLL_LISTING_ATTEMPTS)
            _keep_listing(listing)
    return listing


def _listing_for_build():
    """The cached listing, or a read with every attempt of a download (see spec RN-28)."""
    listing = _cached_listing()
    if listing is None:
        listing = download.read_listing()
        _keep_listing(listing)
    return listing


def _download_size(listing):
    """Sum over the source registry of the listed sizes."""
    return sum(listing[source.name].size for source in sources.SOURCES)


def _running_build():
    """The queued or running build job, or None; an orphan is reported failed by get_job."""
    for job_id in active_build_job_ids():
        job = jobs.get_job(job_id)
        if job is not None and job.status in ACTIVE_STATUSES:
            return job
    return None


def _job_to_show(ready):
    """The running build job, or the latest one when it failed and the database is not ready."""
    job_id = latest_build_job_id()
    job = jobs.get_job(job_id) if job_id is not None else None
    if job is None:
        return None
    if job.status in ACTIVE_STATUSES or (job.status == Job.Status.FAILED and not ready):
        return job
    return None
