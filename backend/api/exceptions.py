"""DRF exception handler: every API error answers in the error envelope.
Details: specs/plan.md, section 6.
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from core.errors import (
    CODE_BAD_REQUEST,
    CODE_CONFIG_INVALID,
    CODE_DATABASE_BUSY,
    CODE_DATABASE_NOT_READY,
    CODE_GENERATION_RUNNING,
    CODE_INSUFFICIENT_SPACE,
    CODE_INTERNAL,
    CODE_METHOD_NOT_ALLOWED,
    CODE_NOT_FOUND,
    CODE_PROVIDER_NOT_AVAILABLE_YET,
    CODE_SOURCE_UNREACHABLE,
    CODE_VALIDATION,
    INTERNAL_MESSAGE,
    MappedError,
    database_busy_error,
    error_body,
)

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "This API path does not exist."
VALIDATION_MESSAGE = "Some request fields are invalid. Correct them and try again."
CARD_NOT_FOUND_MESSAGE = "The card does not exist."
FIELD_FALLBACK_MESSAGE = "This value is not valid."
# Fixed field messages by DRF error code; DRF's own texts may quote the submitted value.
FIELD_MESSAGES = {
    "required": "This field is required.",
    "null": "This field cannot be empty.",
    "blank": "This field cannot be blank.",
    "empty": "This list cannot be empty.",
    "invalid": FIELD_FALLBACK_MESSAGE,
    "invalid_choice": "This value is not one of the allowed choices.",
    "not_a_list": "This value must be a list.",
    "max_length": "This value is too long.",
    "min_length": "This value is too short.",
    "max_value": "This value is too large.",
    "min_value": "This value is too small.",
    "max_string_length": "This value is too large.",
    "max_digits": "This value has too many digits.",
    "max_decimal_places": "This value has too many decimal places.",
    "does_not_exist": "This value does not name an existing item.",
}
BAD_REQUEST_MESSAGE = "Card Factory could not read this request: it must be JSON and accept a JSON answer."

# HTTP status of each mapped error code raised by a view; any other code answers 500.
MAPPED_STATUS = {
    CODE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    CODE_DATABASE_BUSY: status.HTTP_503_SERVICE_UNAVAILABLE,
    CODE_DATABASE_NOT_READY: status.HTTP_503_SERVICE_UNAVAILABLE,
    CODE_INSUFFICIENT_SPACE: status.HTTP_507_INSUFFICIENT_STORAGE,
    CODE_SOURCE_UNREACHABLE: status.HTTP_502_BAD_GATEWAY,
    CODE_CONFIG_INVALID: status.HTTP_400_BAD_REQUEST,
    CODE_PROVIDER_NOT_AVAILABLE_YET: status.HTTP_400_BAD_REQUEST,
    CODE_GENERATION_RUNNING: status.HTTP_409_CONFLICT,
}


def exception_handler(exc, context):
    """Shape any exception raised in a view as an envelope response."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    set_rollback()
    busy = database_busy_error(exc)
    if busy is not None:
        exc = busy
    if isinstance(exc, MappedError):
        http_status = MAPPED_STATUS.get(exc.code)
        if http_status is None:
            logger.warning("Mapped error code %s has no HTTP status; it answers 500.", exc.code)
            http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        return Response(error_body(exc.code, exc.message, exc.setting), status=http_status)
    if isinstance(exc, exceptions.NotFound):
        return Response(error_body(CODE_NOT_FOUND, NOT_FOUND_MESSAGE), status=exc.status_code)
    if isinstance(exc, exceptions.MethodNotAllowed):
        return Response(error_body(CODE_METHOD_NOT_ALLOWED, str(exc.detail)), status=exc.status_code)
    if isinstance(exc, (exceptions.ParseError, exceptions.UnsupportedMediaType, exceptions.NotAcceptable)):
        return Response(error_body(CODE_BAD_REQUEST, BAD_REQUEST_MESSAGE), status=exc.status_code)
    if isinstance(exc, exceptions.ValidationError):
        return Response(
            error_body(CODE_VALIDATION, VALIDATION_MESSAGE, fields=_field_messages(exc)),
            status=exc.status_code,
        )
    # The exception text stays out of the response, since it may quote a value; only the log gets it.
    if isinstance(exc, exceptions.APIException):
        return Response(error_body(CODE_INTERNAL, INTERNAL_MESSAGE), status=exc.status_code)

    logger.exception("Unhandled error in an API view.")
    return Response(error_body(CODE_INTERNAL, INTERNAL_MESSAGE), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _field_messages(exc):
    """`{name: [message]}` from a serializer's error codes, with dotted names for nested fields.

    Only fixed messages chosen by code: DRF texts may quote the submitted value.
    """
    codes = exc.get_codes()
    if not isinstance(codes, dict):
        return None
    fields = {}
    _collect_codes(codes, "", fields)
    return fields or None


def _collect_codes(codes, path, fields):
    if isinstance(codes, dict):
        for key, nested in codes.items():
            _collect_codes(nested, f"{path}.{key}" if path else str(key), fields)
    elif isinstance(codes, list):
        for nested in codes:
            _collect_codes(nested, path, fields)
    else:
        message = FIELD_MESSAGES.get(codes, FIELD_FALLBACK_MESSAGE)
        messages = fields.setdefault(path or "non_field_errors", [])
        if message not in messages:
            messages.append(message)
