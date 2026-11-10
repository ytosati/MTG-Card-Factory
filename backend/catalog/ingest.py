"""Catalog build steps: streaming the bulk files, importing their records and tagging their roles.
Details: specs/plan.md, sections 4, 5, 7, 9.6 and 10.
"""

import codecs
import gzip
import json
import re
import uuid
import zlib
from collections.abc import Iterable, Iterator

from catalog.models import OracleCard

READ_SIZE = 256 * 1024
GZIP_MAGIC = b"\x1f\x8b"
# Upper bound on one undecoded record or line, so a malformed file cannot grow the buffer without end.
MAX_RECORD_CHARS = 16 * 1024 * 1024
BATCH_SIZE = 500

# Records that are not cards a deck can hold.
SKIPPED_LAYOUTS = frozenset(
    {"token", "double_faced_token", "emblem", "art_series", "vanguard", "scheme", "planar"}
)
FACE_FIELDS = ("name", "mana_cost", "type_line", "oracle_text", "colors", "power", "toughness")
FACE_TEXT_SEPARATOR = "\n//\n"


class BulkFileError(ValueError):
    """The bulk file is not a complete JSON array or JSON Lines file of well-formed records."""


class _Prefixed:
    """A binary file whose first bytes were already read, so they can be read again."""

    def __init__(self, prefix, fileobj):
        self._prefix = prefix
        self._file = fileobj

    def read(self, size=-1):
        if not self._prefix:
            return self._file.read(size)
        if size is None or size < 0:
            data, self._prefix = self._prefix + self._file.read(), b""
            return data
        data, self._prefix = self._prefix[:size], self._prefix[size:]
        if len(data) < size:
            data += self._file.read(size - len(data))
        return data


class _Gunzipped:
    """The decompressed bytes of a gzip file; a damaged or truncated file raises BulkFileError."""

    def __init__(self, fileobj):
        self._gzip = gzip.GzipFile(fileobj=fileobj, mode="rb")

    def read(self, size=-1):
        try:
            return self._gzip.read(size)
        except (EOFError, zlib.error, gzip.BadGzipFile) as error:
            raise BulkFileError("the compressed bulk file is truncated or damaged") from error


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
    """Yield each record of the binary `fileobj`, in order, reading bounded chunks.

    The file is a JSON array or JSON Lines (one record per line), either one gzip-compressed or not.
    """
    head = fileobj.read(len(GZIP_MAGIC))
    fileobj = _Prefixed(head, fileobj)
    if head == GZIP_MAGIC:
        fileobj = _Gunzipped(fileobj)
    stream = _TextStream(fileobj)

    first = stream.peek()
    if first == "[":
        yield from _iter_json_array(stream)
    elif first == "{":
        yield from _iter_json_lines(stream)
    else:
        raise BulkFileError("the bulk file is neither a JSON array nor JSON Lines")


def _iter_json_lines(stream) -> Iterator[dict]:
    while stream.peek() != "":
        end = stream.buffer.find("\n", stream.pos)
        while end < 0:
            held = len(stream.buffer) - stream.pos
            if held > MAX_RECORD_CHARS:
                raise BulkFileError("the bulk file has a line that is too long")
            if not stream.grow(max(2 * held, READ_SIZE)):
                end = len(stream.buffer)
                break
            end = stream.buffer.find("\n", stream.pos)
        if end - stream.pos > MAX_RECORD_CHARS:
            raise BulkFileError("the bulk file has a line that is too long")
        line = stream.buffer[stream.pos : end]
        stream.pos = end + 1
        try:
            record = json.loads(line)
        except ValueError as error:  # JSONDecodeError, or a number too long to convert
            raise BulkFileError("the bulk file has a malformed line") from error
        if not isinstance(record, dict):
            raise BulkFileError("the bulk file holds a value that is not a record")
        yield record


def _iter_json_array(stream) -> Iterator[dict]:
    decoder = json.JSONDecoder()
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


# --- Role tagging (see spec RN-12, specs/plan.md section 9.6) ---------------------------

ROLES = (
    "ramp",
    "card_draw",
    "removal",
    "board_wipe",
    "counterspell",
    "tutor",
    "recursion",
    "tokens",
    "life_gain",
    "protection",
    "combat_boost",
    "mana_fixing",
    "sacrifice_outlet",
    "graveyard_fill",
    "evasion",
)

# Patterns run on lowercased text. Every gap is bounded ({0,n}) and stays inside a sentence,
# so matching is linear in the text length.
_NUMBER = r"(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|x|\d+)"
_EVASION_KEYWORDS = r"(?:flying|menace|shadow|fear|intimidate|horsemanship|skulk)"
_BASIC_LAND_TYPES = re.compile(r"\b(?:plains|island|swamp|mountain|forest)\b")
# Effects done by an opponent or by another permanent's controller (see specs/plan.md, section 9.6).
_NOT_YOURS = r"(?<!opponent )(?<!controller )(?<!that player )"


def _any_of(*patterns: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{pattern})" for pattern in patterns), re.MULTILINE)


_ROLE_PATTERNS = {
    "ramp": _any_of(
        r"\bput (?:a|an|up to \w{1,10}|\w{1,10}) (?:basic )?land cards? [^.\n]{0,60}?onto the battlefield",
        r"\bplay (?:an|two) additional lands?\b",
    ),
    "card_draw": _any_of(rf"{_NOT_YOURS}\bdraws? (?:[\w-]{{1,20}} ){{0,3}}?cards?\b"),
    "removal": _any_of(
        r"\b(?:destroy|exile) (?:up to )?(?:(?:one|two|three|four|five|x|any number of) )?(?:other |another )?"
        r"target (?!player|opponent|spell)(?!(?:[\w-]{1,20},? ){0,3}cards?\b)(?![^.;\n]{0,80}?\byou control\b)",
        r"\bdeals? [^.\n]{0,60}?damage to (?:any target|target (?:[\w-]{1,20} )?(?:creature|planeswalker|permanent|battle))",
        r"\btarget (?:[\w-]{1,20} )?(?:creature|permanent) [^.\n]{0,40}?gets? -(?:\d+|x)/-(?:\d+|x)",
        r"\b(?:each opponent|target player|target opponent) sacrifices\b",
    ),
    "board_wipe": _any_of(
        r"\b(?:destroy|exile) all (?:other )?(?:[\w-]{1,20} )?"
        r"(?:creatures|permanents|artifacts|enchantments|planeswalkers|lands)\b",
        r"\bdeals? [^.\n]{0,40}?damage to each (?:other )?creature",
        r"\b(?:all|each) (?:other )?creatures? [^.\n]{0,30}?gets? -(?:\d+|x)/-(?:\d+|x)",
        r"\breturn all (?:[\w-]{1,20} )?(?:creatures|permanents) [^.\n]{0,40}?to (?:their|its) owners?'? hands?",
    ),
    "counterspell": _any_of(
        r"\bcounter (?:up to \w{1,10} )?(?:other |another )?target [^.\n]{0,60}?\b(?:spell|ability)",
        r"\bcounter (?:that|the chosen) (?:spell|ability)\b",
        r"\bcounter (?:all|each) (?:[\w-]{1,20} )?spells?\b",
    ),
    "recursion": _any_of(
        r"\b(?:return|put) [^.\n]{0,60}?\bcards? from (?:your|a|any|target player's) graveyards? (?:to|onto|into)\b",
        r"\breturn ~ from your graveyard\b",
    ),
    "tokens": _any_of(
        rf"{_NOT_YOURS}\bcreates? [^.\n]{{0,80}}?\btokens?\b",
        r"\b(?:amass|populate|investigate|incubate)\b",
    ),
    "life_gain": _any_of(
        rf"{_NOT_YOURS}\bgains? (?:{_NUMBER} life|that much life|life equal)\b",
        r"\blifelink\b",
    ),
    "protection": _any_of(
        r"(?<!~ )\b(?:gains?|have|has)\b [^.\n]{0,60}?\b(?:hexproof|indestructible|shroud|protection from|ward)\b",
        r"\bprevent all (?:combat )?damage that would be dealt to (?!~)",
        r"\bphases? out\b",
    ),
    "combat_boost": _any_of(r"\bgets? \+(?:\d+|x)/\+(?:\d+|x)\b"),
    "mana_fixing": _any_of(
        r"\bmana of any (?:one )?color\b",
        r"\badd \{[wubrg]\}(?:, \{[wubrg]\}){0,4},? or \{[wubrg]\}",
    ),
    "sacrifice_outlet": _any_of(
        r"\bsacrifice (?:a|an|another|one|two|three|x|any number of) (?:(?:other|nontoken|untapped) )?"
        r"(?:creatures?|permanents?|artifacts?)\b[^.:\n]{0,40}:",
    ),
    "graveyard_fill": _any_of(
        r"(?<!opponent )\bmills?\b",
        r"\bsurveil\b",
        rf"{_NOT_YOURS}(?<!target player )\bdiscards? (?:a|an|one|two|three|x|that|those|your|their|\w{{1,10}} cards?)\b",
        r"\bput the top [^.\n]{0,60}?into (?:your|their|its owner's) graveyards?\b",
    ),
    "evasion": _any_of(
        rf"^(?:[a-z ]{{1,30}}, ){{0,6}}{_EVASION_KEYWORDS}(?:,|$)",
        rf"\b(?:has|have|gains?)\b [^.\n]{{0,40}}?\b{_EVASION_KEYWORDS}\b",
        r"\bcan't be blocked\b",
    ),
}

_LIBRARY_SEARCH = re.compile(r"\bsearch your library for ([^.\n]{0,200})")
_LAND_TO_BATTLEFIELD = re.compile(
    r"\b(?:lands?|plains|islands?|swamps?|mountains?|forests?)\b[^.\n]{0,200}?\bonto the battlefield\b"
)
_MANA_ABILITY = re.compile(r"\badd (?:\{|one mana|two mana|three mana|x mana|an amount|that much)")
_LAND_TYPE = re.compile(r"\bland\b")
_REMINDER_TEXT = re.compile(r"\([^()\n]{0,500}\)")


def tag_roles(type_line: str, oracle_text: str, name: str = "") -> list[str]:
    """Roles of a card from fixed patterns over its rules text and type line, in the order of ROLES."""
    type_line = (type_line or "").lower()
    text = _rules_text(oracle_text, name, type_line)
    found = {role for role, pattern in _ROLE_PATTERNS.items() if pattern.search(text)}

    # Ramp, tutor and fixing also depend on the face's type line (see specs/plan.md, section 9.6).
    faces = text.split(FACE_TEXT_SEPARATOR)
    face_types = type_line.split(" // ")
    if len(face_types) != len(faces):
        face_types = [type_line] * len(faces)
    for face, face_type in zip(faces, face_types):
        is_land = bool(_LAND_TYPE.search(face_type))
        for match in _LIBRARY_SEARCH.finditer(face):
            if not _LAND_TO_BATTLEFIELD.search(match.group(1)):
                found.add("tutor")
            else:
                found.add("mana_fixing" if is_land else "ramp")
        if _MANA_ABILITY.search(face) and not is_land:
            found.add("ramp")
        if len(set(_BASIC_LAND_TYPES.findall(face_type))) >= 2:
            found.add("mana_fixing")

    return [role for role in ROLES if role in found]


def _rules_text(oracle_text: str, name: str, type_line: str) -> str:
    """Lowercased rules text without reminder text, with the card's names replaced by "~"."""
    text = _REMINDER_TEXT.sub("", (oracle_text or "").lower())
    full_name = (name or "").strip().lower()
    names = {full_name}
    if " // " in full_name:
        names.update(face.strip() for face in full_name.split(" // "))
    if "legendary" in type_line:
        names.update(part.split(", ", 1)[0] for part in list(names) if ", " in part)
    for card_name in sorted(filter(None, names), key=len, reverse=True):
        text = re.sub(rf"(?<!\w){re.escape(card_name)}(?!\w)", "~", text)
    return text
