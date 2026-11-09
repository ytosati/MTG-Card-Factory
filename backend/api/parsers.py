"""The API parses JSON only (spec RN-29). Details: specs/plan.md, section 6."""

from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser


class StrictJSONParser(JSONParser):
    """JSONParser that also turns a too deeply nested body into a ParseError, not a server error."""

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            return super().parse(stream, media_type, parser_context)
        except RecursionError:
            raise ParseError() from None
