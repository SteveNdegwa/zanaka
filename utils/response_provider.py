import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied

logger = logging.getLogger(__name__)


class ResponseProvider:
    @staticmethod
    def _response(success: bool, message: str, status: int, data=None, error=None) -> JsonResponse:
        return JsonResponse({
            "success": success,
            "message": message,
            "data": data or {},
            "error": error or "",
            "code": status,
        }, status=status)

    @classmethod
    def handle_exception(cls, ex: Exception) -> JsonResponse:
        if isinstance(ex, ValidationError):
            return cls._response(False, "Validation error", 400, error=str(ex))
        elif isinstance(ex, ObjectDoesNotExist):
            return cls._response(False, "Resource not found", 404, error=str(ex))
        elif isinstance(ex, PermissionDenied):
            return cls._response(False, "Forbidden", 403, error=str(ex))
        else:
            return cls._response(False, "Server error", 500, error=str(ex))

    @classmethod
    def success(cls, message="Success", data=None):
        return cls._response(True, message, 200, data=data)

    @classmethod
    def created(cls, message="Created", data=None):
        return cls._response(True, message, 201, data=data)

    @classmethod
    def unauthorized(cls, message="Unauthorized", error=None):
        return cls._response(False, message, 401, error=error)

    @classmethod
    def bad_request(cls, message="Bad Request", error=None):
        return cls._response(False, message, 400, error=error)

