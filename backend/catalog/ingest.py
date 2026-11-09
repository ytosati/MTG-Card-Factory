"""Catalog build steps: streaming the bulk files and importing their records.
Details: specs/plan.md, sections 4, 5, 7 and 10.
"""

import codecs
import json
import uuid
from collections.abc import Iterable, Iterator

from catalog.models import OracleCard

READ_SIZE = 256 * 1024
# Upper bound on one undecoded record, so a malformed file cannot grow the buffer without end.
MAX_RECORD_CHARS = 16 * 1024 * 1024
BATCH_SIZE = 500

# Records that are not cards a deck can hold.
SKIPPED_LAYOUTS = frozenset(
    {"token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"}
)
FACE_FIELDS = ("name", "mana_cost", "type_line", "oracle_text", "colors", "power", "toughness")
FACE_TEXT_SEPARATOR = "\n//\n"


class BulkFileError(ValueError):
    """The bulk file is not a complete JSON array of well-formed records."""


class _TextStream:
    """Decoded text of a binary file, consumed from `pos`, refilled in bounded chunks."""

    def __init__(self, fileobj):
        self._file = fileobj
        # utf-8-sig accepts a byte order mark at the start of the file.
        self._decoder = codecs.getincrementaldecoder("utf-8-sig")()
        self.buffer = ""
        self.pos = 0
        self.eof = False

    def _read(self) -> str:
        chunk = self._file.read(READ_SIZE)
        try:
            if not chunk:
                self.eof = True
                return self._decoder.decode(b"", final=True)
            return self._decoder.decode(chunk)
        except UnicodeDecodeError as error:
            raise BulkFileError("the bulk file is not valid UTF-8") from error

    def grow(self, target: int) -> bool:
        """Append text until at least `target` unconsumed characters are held; False at end of file."""
        if self.eof:
            return False
        parts = [self.buffer[self.pos :]]
        held = len(parts[0])
        while held < target and not self.eof:
            text = self._read()
            parts.append(text)
            held += len(text)
        self.buffer = "".join(parts)
        self.pos = 0
        return True

    def peek(self) -> str:
        """Skip whitespace and return the next character without consuming it ("" at end of file)."""
        while True:
            while self.pos < len(self.buffer) and self.buffer[self.pos].isspace():
                self.pos += 1
            if self.pos < len(self.buffer):
                return self.buffer[self.pos]
            if not self.grow(1):
                return ""


def iter_bulk_records(fileobj) -> Iterator[dict]:
    """Yield each object of the JSON array in the binary `fileobj`, in order, reading bounded chunks."""
    decoder = json.JSONDecoder()
    stream = _TextStream(fileobj)

    if stream.peek() != "[":
        raise BulkFileError("the bulk file does not start with a JSON array")
    stream.pos += 1
    first = True

    while True:
        char = stream.peek()
        if char == "]":
            stream.pos += 1
            if stream.peek() != "":
                raise BulkFileError("the bulk file has data after the closing bracket")
            return
        if not first:
            if char != ",":
                raise BulkFileError("the bulk file is truncated or malformed")
            stream.pos += 1
            stream.peek()
        while True:
            try:
                record, end = decoder.raw_decode(stream.buffer, stream.pos)
                break
            except ValueError as error:  # JSONDecodeError, or a number too long to convert
                # The record may be cut at the chunk boundary; doubling what is held keeps retries linear.
                held = len(stream.buffer) - stream.pos
                if held > MAX_RECORD_CHARS or not stream.grow(max(2 * held, READ_SIZE)):
                    raise BulkFileError("the bulk file is truncated or malformed") from error
        if not isinstance(record, dict):
            raise BulkFileError("the bulk file holds a value that is not a record")
        stream.pos = end
        first = False
        yield record


def oracle_row(record: dict) -> dict | None:
    """OracleCard fields of one Oracle Cards record as plain JSON values, or None when it is not a card."""
    if record.get("layout") in SKIPPED_LAYOUTS:
        return None
    faces = record.get("card_faces") or []
    front = faces[0] if faces else {}
    raw_id = record.get("oracle_id") or front.get("oracle_id")
    if not raw_id:
        return None
    try:
        oracle_id = str(uuid.UUID(raw_id))
    except (TypeError, ValueError, AttributeError) as error:
        raise BulkFileError("a bulk file record has an invalid oracle id") from error
    if not record.get("name"):
        raise BulkFileError(f"the bulk file record {oracle_id} has no name")

    mana_cost = record.get("mana_cost")
    if mana_cost is None:
        mana_cost = front.get("mana_cost", "")
    oracle_text = record.get("oracle_text")
    if oracle_text is None:
        oracle_text = FACE_TEXT_SEPARATOR.join(face.get("oracle_text", "") for face in faces)
    colors = record.get("colors")
    if colors is None:
        colors = []
        for face in faces:
            colors.extend(color for color in face.get("colors", []) if color not in colors)
    type_line = record.get("type_line")
    if type_line is None:
        type_line = " // ".join(face.get("type_line", "") for face in faces)

    return {
        "oracle_id": oracle_id,
        "name": record["name"],
        "mana_cost": mana_cost,
        "cmc": record.get("cmc", front.get("cmc", 0.0)),
        "type_line": type_line,
        "oracle_text": oracle_text,
        "colors": colors,
        "color_identity": record.get("color_identity", []),
        "keywords": record.get("keywords", []),
        "power": record.get("power"),
        "toughness": record.get("toughness"),
        "layout": record.get("layout", ""),
        "faces": [{key: face[key] for key in FACE_FIELDS if key in face} for face in faces],
        "commander_legality": _commander_legality(record.get("legalities") or {}),
        "game_changer": bool(record.get("game_changer", False)),
        "edhrec_rank": record.get("edhrec_rank"),
    }


def import_oracle(records: Iterable[dict]) -> None:
    """Store one OracleCard per Oracle Cards record (see spec RN-01, RN-04)."""
    import_oracle_rows(row for row in map(oracle_row, records) if row is not None)


def import_oracle_rows(rows: Iterable[dict]) -> None:
    """Store rows built by `oracle_row`, keeping the first row of each oracle id."""
    seen = set()
    batch = []
    for row in rows:
        if row["oracle_id"] in seen:
            continue
        seen.add(row["oracle_id"])
        batch.append(OracleCard(**row))
        if len(batch) >= BATCH_SIZE:
            OracleCard.objects.bulk_create(batch)
            batch = []
    if batch:
        OracleCard.objects.bulk_create(batch)


def _commander_legality(legalities: dict) -> str:
    """Stored Commander legality of a record (see specs/plan.md, section 4)."""
    value = legalities.get("commander")
    if value in ("legal", "restricted"):
        return OracleCard.CommanderLegality.LEGAL.value
    if value == "banned":
        return OracleCard.CommanderLegality.BANNED.value
    return OracleCard.CommanderLegality.NOT_LEGAL.value
