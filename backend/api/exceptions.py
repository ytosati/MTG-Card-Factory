"""DRF exception handler: every API error answers in the error envelope.
Details: specs/plan.md, section 6.
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from api.permissions import CODE_DATABASE_NOT_READY
from catalog.download import CODE_INSUFFICIENT_SPACE, CODE_SOURCE_UNREACHABLE
from core.errors import CODE_INTERNAL, INTERNAL_MESSAGE, MappedError, error_body

logger = logging.getLogger(__name__)

CODE_NOT_FOUND = "not_found"
CODE_METHOD_NOT_ALLOWED = "method_not_allowed"
CODE_BAD_REQUEST = "bad_request"

NOT_FOUND_MESSAGE = "This API path does not exist."
BAD_REQUEST_MESSAGE = "Card Factory could not read this request: it must be JSON and accept a JSON answer."

# HTTP status of each mapped error code raised by a view; any other code answers 500.
MAPPED_STATUS = {
    CODE_DATABASE_NOT_READY: status.HTTP_503_SERVICE_UNAVAILABLE,
    CODE_INSUFFICIENT_SPACE: status.HTTP_507_INSUFFICIENT_STORAGE,
    CODE_SOURCE_UNREACHABLE: status.HTTP_502_BAD_GATEWAY,
}


def exception_handler(exc, context):
    """Shape any exception raised in a view as an envelope response."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    set_rollback()
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
    # The exception text stays out of the response, since it may quote a value; only the log gets it.
    if isinstance(exc, exceptions.APIException):
        return Response(error_body(CODE_INTERNAL, INTERNAL_MESSAGE), status=exc.status_code)

    logger.exception("Unhandled error in an API view.")
    return Response(error_body(CODE_INTERNAL, INTERNAL_MESSAGE), status=status.HTTP_500_INTERNAL_SERVER_ERROR)

