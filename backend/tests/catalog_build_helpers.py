"""Test helpers for the catalog build (task T21): a fictional data source served by a
fake transport, hand-written bulk files and SQL-level fault injection.

Details: specs/plan.md, sections 7 (all-or-nothing build) and 10 (data sources).
Every card and every value below is fictional and written by hand. No helper
touches the network: the transport answers from memory.
"""

import errno
import gzip
import hashlib
import http.client
import json
import re
from contextlib import contextmanager

LISTING_URL = "https://api.scryfall.com/bulk-data"
# The current listing: gzip-compressed JSON Lines, listed with `jsonl_download_uri` and `compressed_size`.
ORACLE_URI = "https://data.scryfall.io/oracle-cards/oracle-cards-20261108220423.jsonl.gz"
DEFAULT_CARDS_URI = "https://data.scryfall.io/default-cards/default-cards-20261108220423.jsonl.gz"
# The older listing: one uncompressed JSON array, listed with `download_uri` and `size`.
LEGACY_ORACLE_URI = "https://data.scryfall.io/oracle-cards/fictional-oracle-cards-20261108220423.json"
LEGACY_DEFAULT_CARDS_URI = "https://data.scryfall.io/default-cards/fictional-default-cards-20261108220423.json"
PUBLISHED_AT = "2026-11-08T22:04:23.142+00:00"
NEWER_PUBLISHED_AT = "2026-11-09T10:15:00+00:00"
ORACLE_SOURCE = "scryfall_oracle"
ETAG = '"fictional-build-etag"'
CHUNK = 4096

# Tables the build may write: the catalog app and the card full-text table (plan section 7).
CATALOG_TABLE_PREFIXES = ("catalog_", "oracle_fts")


def _oracle_id(number):
    return f"b2000000-0000-4000-8000-{number:012d}"


LONG_TEXT = ("Whenever a “fictional” spell resolves, scry 1 — ünïcödé ✦ [brackets] {braces} \\ backslash. " * 220).strip()

# Fictional Oracle Cards records, shaped as in the bulk file.
SENTRY = {
    "object": "card",
    "oracle_id": _oracle_id(1),
    "name": "Mossvale Lorekeeper",
    "layout": "normal",
    "mana_cost": "{2}{U}",
    "cmc": 3.0,
    "type_line": "Creature — Merfolk Wizard",
    "oracle_text": "When Mossvale Lorekeeper enters, draw two cards.",
    "power": "1",
    "toughness": "3",
    "colors": ["U"],
    "color_identity": ["U"],
    "keywords": [],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 1200,
}

REMOVAL = {
    "object": "card",
    "oracle_id": _oracle_id(2),
    "name": "Quellbolt Verdict",
    "layout": "normal",
    "mana_cost": "{1}{B}",
    "cmc": 2.0,
    "type_line": "Instant",
    "oracle_text": "Destroy target creature. Its controller gains 2 life.",
    "colors": ["B"],
    "color_identity": ["B"],
    "keywords": [],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 300,
}

TWO_FACED = {
    "object": "card",
    "oracle_id": _oracle_id(3),
    "name": "Ashgrove Pact // Ashgrove Ruin",
    "layout": "modal_dfc",
    "cmc": 4.0,
    "type_line": "Sorcery // Land",
    "color_identity": ["G"],
    "keywords": [],
    "card_faces": [
        {
            "object": "card_face",
            "name": "Ashgrove Pact",
            "mana_cost": "{3}{G}",
            "type_line": "Sorcery",
            "oracle_text": "Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.",
            "colors": ["G"],
        },
        {
            "object": "card_face",
            "name": "Ashgrove Ruin",
            "mana_cost": "",
            "type_line": "Land",
            "oracle_text": "{T}: Add {G}.",
            "colors": [],
        },
    ],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": None,
}

BANNED = {
    "object": "card",
    "oracle_id": _oracle_id(4),
    "name": "Sunken Treasury of Ilvar",
    "layout": "normal",
    "mana_cost": "{0}",
    "cmc": 0.0,
    "type_line": "Artifact",
    "oracle_text": "{T}: Add three mana of any one color.",
    "colors": [],
    "color_identity": [],
    "keywords": [],
    "legalities": {"commander": "banned"},
    "game_changer": True,
    "edhrec_rank": 90,
}

# Text that would break a full-text query built from text: quotes, operators, stars.
ODD_TEXT = {
    "object": "card",
    "oracle_id": _oracle_id(5),
    "name": "Ys'gharr, \"The Unquoted\" * NEAR",
    "layout": "normal",
    "mana_cost": "{W/U}{W/U}{2/R}",
    "cmc": 4.0,
    "type_line": "Legendary Creature — Horror AND NOT Spirit",
    "oracle_text": "Flying\n\"Quoted\" AND NOT * NEAR( '); DROP TABLE oracle_fts; -- ünïcödé ✦ tail",
    "power": "*",
    "toughness": "1+*",
    "colors": ["W", "U", "R"],
    "color_identity": ["W", "U", "R"],
    "keywords": ["Flying"],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 22000,
}

HUGE_TEXT = {
    "object": "card",
    "oracle_id": _oracle_id(6),
    "name": "Endless Chronicle of Varrow",
    "layout": "saga",
    "mana_cost": "{3}{U}",
    "cmc": 4.0,
    "type_line": "Enchantment — Saga",
    "oracle_text": LONG_TEXT,
    "colors": ["U"],
    "color_identity": ["U"],
    "keywords": [],
    "legalities": {"commander": "not_legal"},
    "game_changer": False,
    "edhrec_rank": 45000,
}

# Not a card a deck can hold: skipped by the import.
TOKEN = {
    "object": "card",
    "oracle_id": _oracle_id(7),
    "name": "Mossvale Spirit",
    "layout": "token",
    "mana_cost": "",
    "cmc": 0.0,
    "type_line": "Token Creature — Spirit",
    "oracle_text": "Flying",
    "colors": ["W"],
    "color_identity": ["W"],
    "keywords": ["Flying"],
    "legalities": {"commander": "not_legal"},
}

# A second record with the same oracle id as SENTRY: stored once.
SENTRY_REPEATED = dict(SENTRY, name="Mossvale Lorekeeper", edhrec_rank=1201)

# Only in the newer bulk file: replaces BANNED.
NEWCOMER = {
    "object": "card",
    "oracle_id": _oracle_id(8),
    "name": "Glimmerhusk Courier",
    "layout": "normal",
    "mana_cost": "{1}{W}",
    "cmc": 2.0,
    "type_line": "Creature — Bird Advisor",
    "oracle_text": "Flying\nWhen Glimmerhusk Courier enters, create a 1/1 white Spirit creature token.",
    "power": "1",
    "toughness": "1",
    "colors": ["W"],
    "color_identity": ["W"],
    "keywords": ["Flying"],
    "legalities": {"commander": "legal"},
    "game_changer": False,
    "edhrec_rank": 5100,
}

RECORDS = [SENTRY, REMOVAL, TWO_FACED, BANNED, ODD_TEXT, HUGE_TEXT, TOKEN, SENTRY_REPEATED]
# The cards a build of RECORDS stores (tokens skipped, repeated oracle id once).
CARD_IDS = {_oracle_id(n) for n in (1, 2, 3, 4, 5, 6)}

# The newer bulk file: BANNED removed, NEWCOMER added, REMOVAL text changed.
REMOVAL_REWORDED = dict(REMOVAL, oracle_text="Exile target creature or planeswalker.")
NEWER_RECORDS = [SENTRY, REMOVAL_REWORDED, TWO_FACED, ODD_TEXT, HUGE_TEXT, NEWCOMER]
NEWER_CARD_IDS = {_oracle_id(n) for n in (1, 2, 3, 5, 6, 8)}


def array_bytes(records=None):
    """A bulk file in the older layout: one JSON array, UTF-8, records on their own lines."""
    records = RECORDS if records is None else records
    return ("[\n" + ",\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n]\n").encode(
        "utf-8"
    )


def jsonl_bytes(records=None):
    """JSON Lines, UTF-8: one record per line, each line ended by a newline."""
    records = RECORDS if records is None else records
    return "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records).encode("utf-8")


def gzip_bytes(data):
    """`data` gzip-compressed with a fixed header time, so its size never changes between runs."""
    return gzip.compress(data, mtime=0)


def bulk_bytes(records=None, *, legacy=False):
    """A bulk file as the data source publishes it: gzip-compressed JSON Lines (the current layout),
    or with `legacy` the older uncompressed JSON array."""
    return array_bytes(records) if legacy else gzip_bytes(jsonl_bytes(records))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _headers(values):
    message = http.client.HTTPMessage()
    for name, value in values.items():
        message[name] = value
    return message


class FakeResponse:
    """A response of the transport seam of catalog.download (status, headers, chunks, close)."""

    def __init__(self, status, headers=None, body=b"", cut_after=None):
        self.status = status
        self.headers = _headers(headers or {})
        self._body = body
        self._cut_after = cut_after
        self.closed = False

    @property
    def chunks(self):
        return self._generate()

    def _generate(self):
        limit = len(self._body) if self._cut_after is None else self._cut_after
        for start in range(0, limit, CHUNK):
            yield self._body[start : min(start + CHUNK, limit)]
        if self._cut_after is not None:
            raise ConnectionResetError(errno.ECONNRESET, "Connection reset by peer")

    def close(self):
        self.closed = True


class FakeDataSource:
    """A fictional data source: the download listing and the Oracle Cards bulk file.

    By default the listing is the current one (`jsonl_download_uri` and
    `compressed_size`) and the bulk file is gzip-compressed JSON Lines, served as
    raw gzip (Content-Type application/gzip, no Content-Encoding). With `legacy`
    the listing names `download_uri` and `size` and the bulk file is one JSON array.
    `bulk` is the served bulk file (raw bytes, sent as given). `listing_status`
    answers the listing with that status.`cut_bulk` drops every bulk download halfway. `listing_body` overrides
    the listing bytes (for a malformed listing). `on_request(url)` is called before
    each answer, from inside the build. Every request is kept in `requests`.
    """

    def __init__(
        self,
        bulk=None,
        published_at=PUBLISHED_AT,
        listing_status=200,
        cut_bulk=False,
        listing_body=None,
        on_request=None,
        legacy=False,
    ):
        self.legacy = legacy
        self.oracle_uri = LEGACY_ORACLE_URI if legacy else ORACLE_URI
        self.bulk = bulk_bytes(legacy=legacy) if bulk is None else bulk
        self.published_at = published_at
        self.listing_status = listing_status
        self.cut_bulk = cut_bulk
        self.listing_body = listing_body
        self.on_request = on_request
        self.requests = []
        self.unexpected = []

    def listing(self):
        if self.listing_body is not None:
            return self.listing_body
        if self.legacy:
            files = [
                {"type": "default_cards", "download_uri": LEGACY_DEFAULT_CARDS_URI, "size": 987654},
                {"type": "oracle_cards", "download_uri": LEGACY_ORACLE_URI, "size": len(self.bulk)},
            ]
            encoding = {"content_type": "application/json", "content_encoding": "gzip"}
        else:
            files = [
                {"type": "default_cards", "jsonl_download_uri": DEFAULT_CARDS_URI, "compressed_size": 987654},
                {"type": "oracle_cards", "jsonl_download_uri": ORACLE_URI, "compressed_size": len(self.bulk)},
            ]
            encoding = {"content_type": "application/jsonl", "content_encoding": "gzip"}
        names = {"default_cards": "Fictional Default Cards", "oracle_cards": "Fictional Oracle Cards"}
        ids = {
            "default_cards": "00000000-0000-4000-8000-0000000000d1",
            "oracle_cards": "00000000-0000-4000-8000-0000000000a1",
        }
        entries = [
            {
                "object": "bulk_data",
                "id": ids[item["type"]],
                "type": item["type"],
                "name": names[item["type"]],
                **{key: value for key, value in item.items() if key != "type"},
                "updated_at": self.published_at,
                **encoding,
            }
            for item in files
        ]
        return json.dumps({"object": "list", "has_more": False, "data": entries}).encode("utf-8")

    def urls(self):
        return [url for url, _ in self.requests]

    def __call__(self, url, headers):
        self.requests.append((url, {str(name).lower(): value for name, value in dict(headers).items()}))
        if self.on_request is not None:
            self.on_request(url)
        if url == LISTING_URL:
            body = self.listing()
            return FakeResponse(
                self.listing_status,
                {"Content-Type": "application/json; charset=utf-8", "Content-Length": str(len(body))},
                body,
            )
        if url == self.oracle_uri:
            content_type = "application/json" if self.legacy else "application/gzip"
            return FakeResponse(
                200,
                {
                    "Content-Type": content_type,
                    "Content-Length": str(len(self.bulk)),
                    "ETag": ETAG,
                    "Accept-Ranges": "bytes",
                },
                self.bulk,
                cut_after=len(self.bulk) // 2 if self.cut_bulk else None,
            )
        self.unexpected.append(url)
        return FakeResponse(404, {"Content-Length": "0"}, b"")


class NoTransport:
    """A transport that must never be called: it records the call and fails loudly."""

    def __init__(self):
        self.requests = []

    def __call__(self, url, headers):
        self.requests.append(url)
        raise AssertionError(f"The build contacted the data source ({url}) although the database is ready.")


class FakeSleep:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


_WRITE = re.compile(r'^\s*(?:insert(?:\s+or\s+\w+)?\s+into|update(?:\s+or\s+\w+)?|delete\s+from)\s+"?(\w+)"?', re.I)


def written_table(sql):
    """The table an INSERT, UPDATE or DELETE statement writes, lowercased, or None."""
    match = _WRITE.match(str(sql))
    return match.group(1).lower() if match else None


def inserted_table(sql):
    """The table an INSERT statement writes, lowercased, or None."""
    if not str(sql).lstrip().lower().startswith("insert"):
        return None
    return written_table(sql)


class InjectedFailure(RuntimeError):
    """The failure a test injects in the middle of the import."""


@contextmanager
def failing_write(table, error=None):
    """Make the first INSERT into `table` on this thread's connection raise `error`.

    Works at the SQL level, so it does not depend on how the build issues its
    statements. Yields a list that records each refused statement.
    """
    from django.db import connection

    refused = []

    def wrapper(execute, sql, params, many, context):
        if inserted_table(sql) == table and not refused:
            refused.append(sql)
            raise error if error is not None else InjectedFailure(f"injected failure on {table}")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        yield refused


@contextmanager
def writes_recorded():
    """Record the table of every write statement on this thread's connection."""
    from django.db import connection

    tables = []

    def wrapper(execute, sql, params, many, context):
        table = written_table(sql)
        if table is not None:
            tables.append(table)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(wrapper):
        yield tables


def disk_full_operational_error():
    """The error Django raises when SQLite reports a full disk (SQLITE_FULL)."""
    import sqlite3

    from django.db import OperationalError

    cause = sqlite3.OperationalError("database or disk is full")
    cause.sqlite_errorcode = sqlite3.SQLITE_FULL
    cause.sqlite_errorname = "SQLITE_FULL"
    error = OperationalError("database or disk is full")
    error.__cause__ = cause
    return error


def fts_rows():
    """Every row of the card full-text table as (oracle_id UUID, name)."""
    import uuid

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT oracle_id, name FROM oracle_fts")
        return [(uuid.UUID(str(oracle_id)), name) for oracle_id, name in cursor.fetchall()]


def fts_match(query):
    """The oracle ids whose full-text row matches the FTS5 `query` (a parameter)."""
    import uuid

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT oracle_id FROM oracle_fts WHERE oracle_fts MATCH %s", [query])
        return {uuid.UUID(str(row[0])) for row in cursor.fetchall()}


def database_locked_operational_error():
    """The error Django raises when SQLite cannot take the write lock in time (SQLITE_BUSY)."""
    import sqlite3

    from django.db import OperationalError

    cause = sqlite3.OperationalError("database is locked")
    cause.sqlite_errorcode = sqlite3.SQLITE_BUSY
    cause.sqlite_errorname = "SQLITE_BUSY"
    error = OperationalError("database is locked")
    error.__cause__ = cause
    return error


def files_with_bytes(folder, data):
    """Files under `folder` whose whole content equals `data`."""
    from pathlib import Path

    folder = Path(folder)
    if not folder.exists():
        return []
    return [path for path in folder.rglob("*") if path.is_file() and path.read_bytes() == data]
