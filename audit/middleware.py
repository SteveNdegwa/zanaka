import uuid
import json
import logging
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.urls import resolve

from audit.context import RequestContext
from audit.models import RequestLog
from authentication.models import Identity
from utils.common import get_client_ip

logger = logging.getLogger(__name__)


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._process_request(request)

        view_func = None
        view_args = ()
        view_kwargs = {}
        try:
            resolver_match = resolve(request.path)
            view_func = resolver_match.func
            view_args = resolver_match.args
            view_kwargs = resolver_match.kwargs
        except Exception:
            pass

        if view_func:
            self._process_view(request, view_func, view_args, view_kwargs)

        try:
            response = self.get_response(request)
        except Exception as exc:
            self._process_exception(request, exc)
            raise

        response = self._process_response(request, response)
        return response

    @staticmethod
    def _process_request(request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1].strip()

        user = getattr(request, 'user', None)
        if user is None or isinstance(user, AnonymousUser):
            user = None

        is_authenticated = False
        if token:
            identity = Identity.objects.get(
                token=token,
                expires_at__gte=timezone.now(),
                status=Identity.Status.ACTIVE,
            )
            if identity:
                user = identity.user
                is_authenticated = True

        RequestContext.set(
            request=request,
            user=user,
            token=token,
            is_authenticated=is_authenticated,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_id=request.META.get('HTTP_X_REQUEST_ID', str(uuid.uuid4())),
            session_key=getattr(request.session, 'session_key', None),
            request_method=request.method,
            request_path=request.path,
            is_secure=request.is_secure(),
            started_at=timezone.now(),
        )

    @staticmethod
    def _process_view(request, view_func, view_args, view_kwargs):
        view_name = getattr(view_func, '__name__', 'unknown')
        RequestContext.update(
            view_name=view_name,
            view_args=view_args,
            view_kwargs=view_kwargs,
        )

        if not RequestContext.activity_name:
            method = getattr(request, 'method', 'UNKNOWN').upper()
            if view_func.__name__ in ['get', 'post', 'put', 'delete', 'patch']:
                resource = view_func.__qualname__.split('.')[0].replace('View', '')
                RequestContext.update(activity_name=f"{method} {resource}")
            else:
                RequestContext.update(activity_name=f"{method} {view_name}")

    def _process_exception(self, request, exception):
        RequestContext.update(
            exception_type=type(exception).__name__,
            exception_message=str(exception),
        )
        self._save_request_log()

    def _process_response(self, request, response):
        if hasattr(response, 'status_code'):
            RequestContext.update(response_status=response.status_code)

        try:
            if hasattr(response, 'data'):
                response_data = response.data
            elif hasattr(response, 'content') and response.get('Content-Type', '').startswith('application/json'):
                response_data = json.loads(response.content)
            else:
                response_data = getattr(response, 'content', '')
                if isinstance(response_data, bytes):
                    response_data = response_data.decode(errors='ignore')
                response_data = response_data[:2000]
        except Exception:
            response_data = f'<Could not parse response: {type(response).__name__}>'

        RequestContext.update(response_data=response_data)
        self._save_request_log()
        RequestContext.clear()
        return response

    @staticmethod
    def _save_request_log():
        try:
            ctx = RequestContext.get()

            path = ctx.get('request_path', '')
            method = ctx.get('request_method', '').upper()

            # Filter exempted paths
            exempt_paths = ['/health', '/metrics', '/static', '/media', '/cia', '/favicon.ico']
            if any(path.startswith(ep) for ep in exempt_paths):
                return

            started_at = ctx.get('started_at', timezone.now())
            ended_at = timezone.now()
            time_taken = (ended_at - started_at).total_seconds()

            RequestLog.objects.create(
                request_id=ctx.get('request_id'),
                user=ctx.get('user'),
                token=ctx.get('token'),
                is_authenticated=ctx.get('is_authenticated', False),
                ip_address=ctx.get('ip_address'),
                user_agent=ctx.get('user_agent', ''),
                session_key=ctx.get('session_key'),
                request_method=ctx.get('request_method'),
                request_path=ctx.get('request_path'),
                is_secure=ctx.get('is_secure', False),
                view_name=ctx.get('view_name'),
                view_args=ctx.get('view_args'),
                view_kwargs=ctx.get('view_kwargs'),
                activity_name=ctx.get('activity_name'),
                exception_type=ctx.get('exception_type'),
                exception_message=ctx.get('exception_message'),
                started_at=started_at,
                ended_at=ended_at,
                time_taken=time_taken,
                response_status=ctx.get('response_status'),
                response_data=ctx.get('response_data'),
            )
        except Exception as e:
            logger.exception(f"Failed to save RequestLog: {e}")

