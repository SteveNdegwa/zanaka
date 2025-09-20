import functools

from audit.context import RequestContext
from utils.response_provider import ResponseProvider


def user_login_required(func):
    @functools.wraps(func)
    def wrapper(view, request, *args, **kwargs):
        if not RequestContext.user or not RequestContext.user.is_authenticated:
            return ResponseProvider.unauthorized()
        return func(view, request, *args, **kwargs)
    return wrapper