from django.http import JsonResponse


class ResponseProvider:
    """
    Provides standardized JSON HTTP responses for API endpoints.
    """

    @staticmethod
    def _response(success: bool, message: str, status: int, data=None, error=None) -> JsonResponse:
        """
        Internal helper to generate consistent JSON responses.

        :param success: Whether the request was successful.
        :type success: bool
        :param message: Response message.
        :type message: str
        :param status: HTTP status code.
        :type status: int
        :param data: Optional payload data.
        :type data: dict | None
        :param error: Optional error details.
        :type error: str | None
        :return: Standardized JsonResponse.
        :rtype: JsonResponse
        """
        return JsonResponse({
            'success': success,
            'message': message,
            'data': data or {},
            'error': error or '',
            'code': status,
        }, status=status)

    @staticmethod
    def success(message: str = 'Success', data: dict | None = None) -> JsonResponse:
        return ResponseProvider._response(True, message, 200, data=data)

    @staticmethod
    def created(message: str = 'Created', data: dict | None = None) -> JsonResponse:
        return ResponseProvider._response(True, message, 201, data=data)

    @staticmethod
    def error(message: str = 'Error', error: str | None = None) -> JsonResponse:
        return ResponseProvider._response(False, message, 400, error=error)

    @staticmethod
    def not_found(message: str = 'Not found') -> JsonResponse:
        return ResponseProvider._response(False, message, 404)

    @staticmethod
    def unauthorized(message: str = 'Not authenticated') -> JsonResponse:
        return ResponseProvider._response(False, message, 401)

    @staticmethod
    def forbidden(message: str = 'Forbidden') -> JsonResponse:
        return ResponseProvider._response(False, message, 403)

    @staticmethod
    def server_error(message: str = 'Server error') -> JsonResponse:
        return ResponseProvider._response(False, message, 500)
