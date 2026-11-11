"""All-or-nothing catalog build over the source registry, and the build job.
Details: specs/plan.md, sections 7 ("All-or-nothing build", "Catalog version") and 10.
"""

import hashlib
import json
import logging
import sqlite3
import time
from datetime import datetime

from django.db import OperationalError, connection, transaction
from django.utils import timezone

from catalog import download, sources
from catalog.ingest import BulkFileError, import_oracle_rows, iter_bulk_records, oracle_row, tag_roles
from catalog.models import BuildRun, OracleCard, SourceRecord
from catalog.selectors import is_ready
from core import jobs
from core.errors import (
    CODE_INSUFFICIENT_SPACE,
    CODE_INTERNAL,
    CODE_SOURCE_UNREACHABLE,
    MappedError,
    database_busy_error,
)
from core.models import Job
from core.paths import data_dir

logger = logging.getLogger(__name__)

SOURCE_SUFFIX = ".json"
COMPRESSED_SOURCE_SUFFIX = ".jsonl.gz"
SOURCE_INFO_SUFFIX = ".info.json"
EXTRACT_SUFFIX = ".jsonl"
HASH_READ_SIZE = 1024 * 1024

BULK_FILE_MESSAGE = "The data source sent a card file that could not be read. Try again later."
NO_CARDS_MESSAGE = "The data source sent a card file with no cards. Try again later."
READ_FAILURE_MESSAGE = (
    "Could not read a file the build prepared in the data folder. Check that no other program "
    "holds it, then try again."
)

# Progress marks: the downloads take most of the time, the import is one short transaction.
LISTING_READ = 0.05
DOWNLOADS_DONE = 0.7
EXTRACTED = 0.85

# Fixed statements: the card full-text table is a virtual table the ORM does not manage.
_CLEAR_FTS = "DELETE FROM oracle_fts"
_FILL_FTS = (
    "INSERT INTO oracle_fts(oracle_id, name, type_line, oracle_text) "
    "SELECT oracle_id, name, type_line, oracle_text FROM catalog_oraclecard"
)


def run_build(*, transport=None, sleep=None, report=None):
    """Build the reference database unless it is ready for the current catalog version (see spec RN-01, RN-03)."""
    report = report if report is not None else _no_report
    if is_ready():
        report(1.0)
        return
    started_at = timezone.now()
    report(0.0)
    # Complete downloads are kept after a failure so a retry reuses them (see spec RN-28); extracts never are.
    kept = []
    extracts = {}
    try:
        # Phase 1, outside any transaction: nothing here is marked ready.
        listing = download.read_listing(transport=transport, sleep=sleep)
        report(LISTING_READ)
        downloaded = []
        for number, source in enumerate(sources.SOURCES, start=1):
            entry = listing[source.name]
            result, downloaded_at = _fetch(source, entry, transport, sleep)
            kept.extend(_source_files(source, entry))
            downloaded.append((source, entry, result, downloaded_at))
            report(LISTING_READ + (DOWNLOADS_DONE - LISTING_READ) * number / len(sources.SOURCES))
        for source, entry, result, _ in downloaded:
            extract = result.path.with_name(source.name + EXTRACT_SUFFIX)
            extracts[source.name] = extract
            try:
                _EXTRACTORS[source.name](result.path, extract)
            except BaseException:
                # A file that cannot be extracted is never reused: the retry downloads it again.
                _remove(_source_files(source, entry))
                raise
        report(EXTRACTED)
        _import(downloaded, extracts, started_at)
    except MappedError as error:
        if error.code == CODE_INSUFFICIENT_SPACE:
            _remove(kept)
        raise
    else:
        _remove(kept)
    finally:
        _remove(extracts.values())
    report(1.0)


def start_build(*, transport=None, sleep=None):
    """Submit the build as a job of kind build; call it outside `transaction.atomic()` (see core.jobs.submit)."""
    return jobs.submit(Job.Kind.BUILD, lambda report: run_build(transport=transport, sleep=sleep, report=report))


def _no_report(progress):
    pass


def _source_files(source, entry):
    """The downloaded file of `source`, named by the format of its listing entry, and its record."""
    folder = data_dir() / "downloads"
    suffix = COMPRESSED_SOURCE_SUFFIX if entry.compressed else SOURCE_SUFFIX
    return [folder / (source.name + suffix), folder / (source.name + SOURCE_INFO_SUFFIX)]


def _fetch(source, entry, transport, sleep):
    """The downloaded file of `source` and its download date, reusing a complete file of the same listing entry."""
    path, info = _source_files(source, entry)
    reused = _reusable(path, info, entry)
    if reused is not None:
        return reused
    result = download.download_file(
        entry.url, path.name, expected_size=entry.size, transport=transport, sleep=sleep
    )
    downloaded_at = timezone.now()
    record = {
        "url": entry.url,
        "size": result.size,
        "published_at": entry.published_at.isoformat(),
        "sha256": result.sha256,
        "downloaded_at": downloaded_at.isoformat(),
    }
    try:
        info.write_text(json.dumps(record), encoding="utf-8")
    except OSError:
        # Only the reuse on a retry is lost; the build goes on.
        logger.warning("The record of a downloaded source could not be written: %s", info.name)
        info.unlink(missing_ok=True)
    return result, downloaded_at


def _reusable(path, info, entry):
    """(DownloadResult, download date) of a kept file that matches `entry` and its recorded checksum, else None."""
    try:
        record = json.loads(info.read_text(encoding="utf-8"))
        if (
            record["url"] != entry.url
            or record["size"] != entry.size
            or record["published_at"] != entry.published_at.isoformat()
            or path.stat().st_size != entry.size
        ):
            return None
        sha = hashlib.sha256()
        with open(path, "rb") as handle:
            while chunk := handle.read(HASH_READ_SIZE):
                sha.update(chunk)
        if sha.hexdigest() != record["sha256"]:
            return None
        downloaded_at = datetime.fromisoformat(record["downloaded_at"])
    except (OSError, ValueError, TypeError, KeyError):
        return None
    return download.DownloadResult(path=path, size=entry.size, sha256=record["sha256"]), downloaded_at


def _extract_oracle(source_path, extract_path):
    """Write one JSON line per card of the Oracle Cards file, roles tagged (plan section 9.6)."""
    count = 0
    try:
        with open(source_path, "rb") as source, open(extract_path, "w", encoding="utf-8", newline="\n") as extract:
            for record in iter_bulk_records(source):
                row = oracle_row(record)
                if row is None:
                    continue
                row["roles"] = tag_roles(row["type_line"], row["oracle_text"], row["name"])
                extract.write(json.dumps(row, ensure_ascii=False))
                extract.write("\n")
                count += 1
    except BulkFileError:
        raise MappedError(CODE_SOURCE_UNREACHABLE, BULK_FILE_MESSAGE) from None
    except OSError as error:
        raise download.file_failure(error) from None
    if count == 0:
        raise MappedError(CODE_SOURCE_UNREACHABLE, NO_CARDS_MESSAGE)


def _import_oracle(extract_path):
    with open(extract_path, encoding="utf-8") as extract:
        import_oracle_rows(json.loads(line) for line in extract)


# Per source: how its file is extracted in phase 1 and how the extract is imported in phase 2.
_EXTRACTORS = {SourceRecord.Source.SCRYFALL_ORACLE: _extract_oracle}
_IMPORTERS = {SourceRecord.Source.SCRYFALL_ORACLE: _import_oracle}


def _import(downloaded, extracts, started_at):
    """Phase 2: one short transaction that writes only catalog tables (plan section 7)."""
    began = time.monotonic()
    try:
        with transaction.atomic():
            # Another build may have finished while this one downloaded.
            if is_ready():
                return
            OracleCard.objects.all().delete()
            SourceRecord.objects.all().delete()
            with connection.cursor() as cursor:
                cursor.execute(_CLEAR_FTS)
            for source, _, _, _ in downloaded:
                _IMPORTERS[source.name](extracts[source.name])
            with connection.cursor() as cursor:
                cursor.execute(_FILL_FTS)
            for source, entry, result, downloaded_at in downloaded:
                SourceRecord.objects.create(
                    source=source.name,
                    url=entry.url,
                    published_at=entry.published_at,
                    downloaded_at=downloaded_at,
                    sha256=result.sha256,
                    size=result.size,
                )
            BuildRun.objects.create(
                catalog_version=sources.CATALOG_VERSION, started_at=started_at, finished_at=timezone.now()
            )
    except OperationalError as error:
        mapped = _mapped_database_error(error)
        if mapped is not None:
            raise mapped from None
        raise
    except OSError:
        raise MappedError(CODE_INTERNAL, READ_FAILURE_MESSAGE) from None
    logger.info("The catalog import transaction took %.2f s.", time.monotonic() - began)


def _mapped_database_error(error):
    """The MappedError of a full disk or a locked database, else None (plan section 6)."""
    cause = error.__cause__
    code = getattr(cause, "sqlite_errorcode", None)
    text = str(error).lower()
    # The low byte is the primary result code; extended codes share it.
    primary = code & 0xFF if isinstance(code, int) else None
    if primary == sqlite3.SQLITE_FULL or (primary is None and "database or disk is full" in text):
        return MappedError(CODE_INSUFFICIENT_SPACE, download.DISK_FULL_MESSAGE)
    return database_busy_error(error)


def _remove(paths):
    """Delete files of this build in `data/downloads/` (plan section 7, data layout)."""
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("A source file of the build could not be deleted: %s", path.name)
