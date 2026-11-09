"""DRF exception handler: every API error answers in the error envelope.
Details: specs/plan.md, section 6.
"""

import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import set_rollback

from core.errors import CODE_INTERNAL, INTERNAL_MESSAGE, error_body

logger = logging.getLogger(__name__)

CODE_NOT_FOUND = "not_found"
CODE_METHOD_NOT_ALLOWED = "method_not_allowed"
CODE_BAD_REQUEST = "bad_request"

NOT_FOUND_MESSAGE = "This API path does not exist."
BAD_REQUEST_MESSAGE = "Card Factory could not read this request: it must be JSON and accept a JSON answer."


def exception_handler(exc, context):
    """Shape any exception raised in a view as an envelope response."""
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    set_rollback()
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

