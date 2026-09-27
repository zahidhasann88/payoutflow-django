from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status as http_status
from rest_framework.response import Response

from .error_codes import ErrorCode

logger = logging.getLogger("payoutflow.api")


class BusinessError(drf_exceptions.APIException):
    """Base class for domain errors with a stable machine-readable code."""

    status_code = http_status.HTTP_400_BAD_REQUEST
    default_detail = "A business rule prevented this operation."
    default_code = "BUSINESS_ERROR"

    def __init__(self, message: str | None = None, code: str | None = None,
                 status_code: int | None = None):
        self.message = message or self.default_detail
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail=self.message, code=self.code)


class ValidationError(BusinessError):
    status_code = http_status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid input."
    default_code = ErrorCode.VALIDATION_ERROR


class UnauthorizedAccess(BusinessError):
    status_code = http_status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = ErrorCode.UNAUTHORIZED_ACCESS


class NotFoundError(BusinessError):
    status_code = http_status.HTTP_404_NOT_FOUND
    default_detail = "Resource not found."
    default_code = ErrorCode.NOT_FOUND


class InvalidStatusTransition(BusinessError):
    status_code = http_status.HTTP_409_CONFLICT
    default_detail = "This status transition is not allowed."
    default_code = ErrorCode.INVALID_STATUS_TRANSITION


def _message_from_detail(detail) -> str:
    """Flatten DRF error detail structures into a single human message."""
    if isinstance(detail, dict):
        parts = []
        for field, value in detail.items():
            text = _message_from_detail(value)
            parts.append(f"{field}: {text}" if field != "detail" else text)
        return " ".join(parts)
    if isinstance(detail, (list, tuple)):
        return " ".join(_message_from_detail(item) for item in detail)
    return str(detail)


def api_exception_handler(exc, context):
    """
    DRF exception handler producing the standard error envelope.

    * ``BusinessError`` subclasses keep their own code/status.
    * DRF ``ValidationError`` → VALIDATION_ERROR (field details preserved in
      ``errors`` for forms).
    * Auth/permission errors → UNAUTHENTICATED / UNAUTHORIZED_ACCESS.
    * Http404 / PermissionDenied → NOT_FOUND / UNAUTHORIZED_ACCESS.
    * Anything else → 500 INTERNAL_ERROR (details logged, not exposed).
    """
    headers = {}
    if isinstance(exc, drf_exceptions.Throttled):
        code = ErrorCode.THROTTLED
        message = "Too many requests. Please slow down."
        status_code = exc.status_code
        headers["Retry-after"] = str(getattr(exc, "wait", "") or "")
    elif isinstance(exc, BusinessError):
        code, message, status_code = exc.code, exc.message, exc.status_code
    elif isinstance(exc, drf_exceptions.ValidationError):
        code = ErrorCode.VALIDATION_ERROR
        message = _message_from_detail(exc.detail)
        status_code = http_status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, drf_exceptions.NotAuthenticated):
        code, message = ErrorCode.UNAUTHENTICATED, "Authentication credentials were not provided."
        status_code = http_status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, (drf_exceptions.PermissionDenied, PermissionDenied)):
        code = ErrorCode.UNAUTHORIZED_ACCESS
        message = "You do not have permission to perform this action."
        status_code = http_status.HTTP_403_FORBIDDEN
    elif isinstance(exc, (Http404, drf_exceptions.NotFound)):
        code, message = ErrorCode.NOT_FOUND, "Resource not found."
        status_code = http_status.HTTP_404_NOT_FOUND
    elif isinstance(exc, drf_exceptions.MethodNotAllowed):
        code, message = ErrorCode.METHOD_NOT_ALLOWED, str(exc.detail)
        status_code = exc.status_code
    elif isinstance(exc, drf_exceptions.APIException):
        code = getattr(exc, "default_code", "API_ERROR").upper()
        message = _message_from_detail(exc.detail)
        status_code = exc.status_code
    else:
        logger.exception("Unhandled exception in %s", context.get("view"), exc_info=exc)
        code, message = ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
        status_code = http_status.HTTP_500_INTERNAL_SERVER_ERROR

    if status_code >= 500:
        logger.error("API error %s: %s", code, message)

    body = {"success": False, "message": message, "code": code}
    if isinstance(exc, drf_exceptions.ValidationError) and isinstance(exc.detail, dict):
        body["errors"] = {
            field: _message_from_detail(value) for field, value in exc.detail.items()
        }
    return Response(body, status=status_code, headers=headers or None)
