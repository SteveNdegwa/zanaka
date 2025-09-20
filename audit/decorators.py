import functools
from audit.context import RequestContext


def set_activity_name(activity_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(view, request, *args, **kwargs):
            RequestContext.update(activity_name=activity_name)
            return func(view, request, *args, **kwargs)
        return wrapper
    return decorator
