import json
import logging
import random
import re
import string

from typing import Optional, Any

from django.core.handlers.wsgi import WSGIRequest

logger = logging.getLogger(__name__)


def get_client_ip(request: WSGIRequest) -> Optional[str]:
    """
    Retrieve the client's IP address from a Django request object.

    :param request: Django HTTP request object.
    :type request: django.http.HttpRequest
    :return: The client IP address as a string, or None if not found.
    :rtype: str | None
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
       return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')


def get_request_data(request: WSGIRequest) -> tuple[dict, dict]:
    """
    Extracts structured data and uploaded files from a Django request.

    :param request: The Django WSGIRequest object.
    :return: A tuple containing:
        - data (dict): Parsed request data.
        - files (dict): Uploaded files keyed by field name.
    :raises: None. Returns empty dicts on error.
    :rtype: tuple[dict, dict]
    """
    try:
        if request is None:
            return {}, {}
        method = request.method
        content_type = request.META.get('CONTENT_TYPE', '')
        data = {}
        files = {}
        if 'application/json' in content_type:
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = {}
        elif method in ['POST', 'PUT', 'PATCH']:
            data = request.POST.dict()
        elif method == 'GET':
            data = request.GET.dict()
        if request.FILES:
            files = {
                key: request.FILES.getlist(key) if len(request.FILES.getlist(key)) > 1
                else request.FILES[key]
                for key in request.FILES
            }
        if not data and request.body:
            # noinspection PyBroadException
            try:
                data = json.loads(request.body)
            except Exception:
                data = {}
        return data, files
    except Exception as ex:
        logger.exception('get_request_data Exception: %s' % ex)
        return {}, {}


def generate_random_password(length=8):
    """
    Generates an alphanumeric password of specified length.

    :param length: Desired password length (>= 6).
    :type length: int
    :return: Generated password.
    :rtype: str
    :raises ValueError: If length is less than 6.
    """
    if length < 6:
        raise ValueError("Password length must be at least 6 characters.")
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def generate_random_pin(length=4):
    """
    Generates a numeric PIN of specified length.

    :param length: Length of the PIN (between 4 and 6).
    :type length: int
    :return: Numeric PIN.
    :rtype: str
    :raises ValueError: If length is not between 4 and 6.
    """
    if not 4 <= length <= 6:
        raise ValueError("PIN length must be between 4 and 6 digits.")
    return ''.join(random.choices(string.digits, k=length))


def sanitize_data(data: Optional[dict]) -> Optional[dict]:
    """
    Redact sensitive fields in a dictionary by masking their values.
    Works recursively for nested dictionaries and lists.

    :param data: Dictionary containing request or user data
    :return: A new dictionary with sensitive values masked
    :rtype: dict
    """
    sensitive_keys = {"password", "old_password", "new_password"}

    if data is None:
        return None

    def _sanitize(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: ("****" if k.lower() in sensitive_keys else _sanitize(v))
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [_sanitize(item) for item in obj]
        else:
            return obj

    return _sanitize(data)


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validates a password against minimum strength requirements.

    The rules enforced are:
    - Length greater than 6 characters
    - Contains at least one uppercase letter
    - Contains at least one digit
    - Contains at least one special character

    :param password: The password string to validate.
    :type password: str
    :returns: A tuple where the first value indicates validity and the second contains an error message if invalid.
    :rtype: tuple[bool, str]
    """
    if len(password) <= 6:
        return False, "Password must be longer than 6 characters."

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit."

    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character."

    return True, ""
